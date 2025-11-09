from flask import Blueprint, request, jsonify, current_app
import os
import logging
import traceback

# Create blueprint with URL prefix
etl_api_blueprint = Blueprint('etl_api', __name__, url_prefix='/api/etl')
logger = logging.getLogger(__name__)

@etl_api_blueprint.route('/process', methods=['POST'])
def process_document():
    """Process a document through the ETL pipeline."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not file.filename.lower().endswith(('.docx', '.pdf')):
        return jsonify({"error": "File must be DOCX or PDF"}), 400
    
    try:
        # Import ETL modules
        from backend.etl import config as etl_config_local
        from backend.etl.main import run_pipeline_for_file
        
        # Ensure input directory exists
        os.makedirs(etl_config_local.INPUT_DIR, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(etl_config_local.INPUT_DIR, file.filename)
        file.save(file_path)
        
        # Run the ETL pipeline
        success, message = run_pipeline_for_file(file_path)
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "filename": file.filename
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message,
                "filename": file.filename
            }), 500
            
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Error in ETL process: {e}\n{stack_trace}")
        return jsonify({
            "success": False,
            "error": str(e),
            "filename": file.filename
        }), 500

@etl_api_blueprint.route('/status', methods=['GET'])
def etl_status():
    """Get the status of the ETL pipeline."""
    try:
        from backend.etl import config as etl_config_local
        import os
        
        # Check if necessary directories exist
        input_dir_exists = os.path.exists(etl_config_local.INPUT_DIR)
        output_dir_exists = os.path.exists(etl_config_local.OUTPUT_DIR)
        processed_dir_exists = os.path.exists(etl_config_local.PROCESSED_DIR)
        
        # Check if weaviate is running
        weaviate_status = "unknown"
        try:
            from weaviate import Client
            from weaviate.exceptions import WeaviateQueryError
            
            client = Client(url=etl_config_local.WEAVIATE_URL)
            client.schema.get()
            weaviate_status = "running"
        except Exception as e:
            weaviate_status = f"error: {str(e)}"
        
        # Check for available models (Claude, OpenAI)
        from backend.app import llm_client, model_name
        llm_status = "available" if llm_client else "not configured"
        
        # Count documents in Weaviate if it's running
        document_count = 0
        if weaviate_status == "running":
            try:
                from backend.etl.agents.opening_agent import query_weaviate_openings_count
                document_count = query_weaviate_openings_count()
            except Exception as e:
                logger.error(f"Error counting documents: {e}")
        
        return jsonify({
            "status": "ok",
            "directories": {
                "input": {
                    "exists": input_dir_exists,
                    "path": etl_config_local.INPUT_DIR
                },
                "output": {
                    "exists": output_dir_exists,
                    "path": etl_config_local.OUTPUT_DIR
                },
                "processed": {
                    "exists": processed_dir_exists,
                    "path": etl_config_local.PROCESSED_DIR
                }
            },
            "weaviate": {
                "status": weaviate_status,
                "url": etl_config_local.WEAVIATE_URL,
                "document_count": document_count
            },
            "llm": {
                "status": llm_status,
                "model": model_name if llm_client else "none"
            }
        }), 200
        
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Error checking ETL status: {e}\n{stack_trace}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500 