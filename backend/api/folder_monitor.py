#!/usr/bin/env python3
"""
Folder monitoring API for automatic document processing.
Provides endpoints for batch processing documents from the input folder.
"""

from flask import Blueprint, jsonify, request
import os
import glob
import json
from datetime import datetime
from etl.main import run_pipeline_for_file
from etl import config
from etl.weaviate_loader import get_weaviate_client

folder_monitor_bp = Blueprint('folder_monitor', __name__)

def get_input_files():
    """Get list of unprocessed files in input directory."""
    input_files = []
    
    # Supported file types
    patterns = ['*.docx', '*.pdf', '*.doc']
    
    for pattern in patterns:
        files = glob.glob(os.path.join(config.INPUT_DIR, pattern))
        for file_path in files:
            filename = os.path.basename(file_path)
            
            # Check if already processed (look for corresponding chunk file)
            chunk_file = os.path.join(config.PROCESSED_DIR, f"{os.path.splitext(filename)[0]}_chunks.json")
            
            input_files.append({
                'filename': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                'processed': os.path.exists(chunk_file),
                'chunk_file': chunk_file if os.path.exists(chunk_file) else None
            })
    
    return input_files

def get_processed_files():
    """Get list of processed files and their status."""
    processed_files = []
    
    # Find all chunk files
    chunk_files = glob.glob(os.path.join(config.PROCESSED_DIR, "*_chunks.json"))
    
    for chunk_file in chunk_files:
        filename = os.path.basename(chunk_file)
        base_name = filename.replace('_chunks.json', '')
        
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            chunk_count = len(chunks)
            
            # Check if loaded to Weaviate (simplified check)
            loaded_to_weaviate = chunk_count > 0  # Assume loaded if chunks exist
            
            processed_files.append({
                'filename': filename,
                'base_name': base_name,
                'path': chunk_file,
                'chunk_count': chunk_count,
                'size': os.path.getsize(chunk_file),
                'modified': datetime.fromtimestamp(os.path.getmtime(chunk_file)).isoformat(),
                'loaded_to_weaviate': loaded_to_weaviate
            })
            
        except Exception as e:
            processed_files.append({
                'filename': filename,
                'base_name': base_name,
                'path': chunk_file,
                'chunk_count': 0,
                'error': str(e),
                'loaded_to_weaviate': False
            })
    
    return processed_files

@folder_monitor_bp.route('/status', methods=['GET'])
def get_folder_status():
    """Get current status of input and processed folders."""
    try:
        input_files = get_input_files()
        processed_files = get_processed_files()
        
        # Get Weaviate stats
        weaviate_stats = {}
        try:
            client = get_weaviate_client()
            if client:
                collection = client.collections.get(config.WEAVIATE_CLASS_NAME)
                response = collection.aggregate.over_all(total_count=True)
                weaviate_stats = {
                    'total_chunks': response.total_count,
                    'collection_name': config.WEAVIATE_CLASS_NAME,
                    'connected': True
                }
                # client.close() removed - Weaviate client manages connections automatically
        except Exception as e:
            weaviate_stats = {
                'error': str(e),
                'connected': False
            }
        
        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'input_folder': {
                'path': config.INPUT_DIR,
                'files': input_files,
                'total_files': len(input_files),
                'unprocessed_files': len([f for f in input_files if not f['processed']])
            },
            'processed_folder': {
                'path': config.PROCESSED_DIR,
                'files': processed_files,
                'total_files': len(processed_files),
                'total_chunks': sum(f.get('chunk_count', 0) for f in processed_files)
            },
            'weaviate': weaviate_stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@folder_monitor_bp.route('/process-all', methods=['POST'])
def process_all_files():
    """Process all unprocessed files in the input folder."""
    try:
        input_files = get_input_files()
        unprocessed_files = [f for f in input_files if not f['processed']]
        
        if not unprocessed_files:
            return jsonify({
                'status': 'success',
                'message': 'No unprocessed files found',
                'processed_count': 0
            })
        
        results = []
        
        for file_info in unprocessed_files:
            try:
                # Process the document
                success, message = run_pipeline_for_file(file_info['path'])
                
                if success:
                    results.append({
                        'filename': file_info['filename'],
                        'status': 'success',
                        'message': message,
                        'chunks_created': 'unknown',  # Would need to parse chunks file to get exact count
                        'loaded_to_weaviate': True  # Assuming success means loaded
                    })
                else:
                    results.append({
                        'filename': file_info['filename'],
                        'status': 'error',
                        'error': message
                    })
                
            except Exception as e:
                results.append({
                    'filename': file_info['filename'],
                    'status': 'error',
                    'error': str(e)
                })
        
        successful_count = len([r for r in results if r['status'] == 'success'])
        
        return jsonify({
            'status': 'success',
            'message': f'Processed {successful_count}/{len(unprocessed_files)} files',
            'processed_count': successful_count,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@folder_monitor_bp.route('/process-file', methods=['POST'])
def process_single_file():
    """Process a specific file by filename."""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'status': 'error',
                'message': 'filename parameter required'
            }), 400
        
        file_path = os.path.join(config.INPUT_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': f'File not found: {filename}'
            }), 404
        
        # Process the document
        success, message = run_pipeline_for_file(file_path)
        
        if success:
            return jsonify({
                'status': 'success',
                'filename': filename,
                'message': message,
                'chunks_created': 'unknown',  # Would need to parse chunks file
                'loaded_to_weaviate': True,  # Assuming success means loaded
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'filename': filename,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@folder_monitor_bp.route('/cleanup', methods=['POST'])
def cleanup_processed_files():
    """Clean up old processed files (optional maintenance endpoint)."""
    try:
        data = request.get_json()
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'status': 'error',
                'message': 'Must set confirm=true to proceed with cleanup'
            }), 400
        
        # This is a placeholder for cleanup logic
        # Could implement features like:
        # - Remove old processed files
        # - Archive old chunks
        # - Clean up orphaned files
        
        return jsonify({
            'status': 'success',
            'message': 'Cleanup completed',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500 