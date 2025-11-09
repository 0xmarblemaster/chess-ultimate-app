"""
Chunking Service

Service for chunking text and handling document processing for the vector database.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
import re
import uuid
import json

# Import config
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

class ChunkingService:
    """
    Service for text chunking operations.
    
    This service handles:
    1. Splitting documents into chunks with overlap
    2. Metadata extraction and management
    3. Chunk processing and normalization
    """
    
    def __init__(self, chunk_size=None, chunk_overlap=None):
        """
        Initialize the Chunking service.
        
        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.logger = logger
        self.chunk_size = chunk_size or CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or CHUNK_OVERLAP
        
    def healthcheck(self) -> bool:
        """
        Check if the service is operational.
        
        Returns:
            True if the service is healthy, False otherwise.
        """
        try:
            # Simple validation of configuration
            if self.chunk_size <= 0:
                self.logger.error(f"Invalid chunk size: {self.chunk_size}")
                return False
                
            if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
                self.logger.error(f"Invalid chunk overlap: {self.chunk_overlap}, must be less than chunk size {self.chunk_size}")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to be chunked
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of dictionaries containing chunks and their metadata
        """
        try:
            # Initialize result list and metadata
            chunks = []
            base_metadata = metadata or {}
            
            # Handle empty text
            if not text or len(text.strip()) == 0:
                self.logger.warning("Empty text provided to chunk_text")
                return []
            
            # Calculate number of chunks needed
            text_length = len(text)
            stride = self.chunk_size - self.chunk_overlap
            
            # Handle case where text is smaller than chunk size
            if text_length <= self.chunk_size:
                chunk_id = str(uuid.uuid4())
                chunks.append({
                    "text": text,
                    "metadata": {
                        **base_metadata,
                        "chunk_id": chunk_id,
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "char_start": 0,
                        "char_end": text_length
                    }
                })
                return chunks
            
            # Chunk the text
            num_chunks = max(1, (text_length - self.chunk_overlap) // stride + 
                            (1 if (text_length - self.chunk_overlap) % stride > 0 else 0))
            
            for i in range(num_chunks):
                # Calculate chunk boundaries
                start = i * stride
                end = min(start + self.chunk_size, text_length)
                
                # Extract the chunk
                chunk_text = text[start:end]
                
                # Create unique ID for this chunk
                chunk_id = str(uuid.uuid4())
                
                # Add to result with metadata
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        **base_metadata,
                        "chunk_id": chunk_id,
                        "chunk_index": i,
                        "total_chunks": num_chunks,
                        "char_start": start,
                        "char_end": end
                    }
                })
            
            self.logger.info(f"Split text into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error in chunk_text: {e}")
            raise

    def chunk_document(self, document_path: Union[str, Path], 
                      metadata: Optional[Dict[str, Any]] = None,
                      extract_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Process a document file and split it into chunks.
        
        Args:
            document_path: Path to the document file
            metadata: Optional metadata to attach to each chunk
            extract_metadata: Whether to extract metadata from the document
            
        Returns:
            List of dictionaries containing chunks and their metadata
            
        Raises:
            FileNotFoundError: If the document cannot be found
            ValueError: If the document format is not supported
        """
        try:
            # Convert to Path if string
            if isinstance(document_path, str):
                document_path = Path(document_path)
                
            # Check if file exists
            if not document_path.exists():
                raise FileNotFoundError(f"Document not found: {document_path}")
                
            # Get file extension
            file_extension = document_path.suffix.lower()
            
            # Initialize metadata
            doc_metadata = metadata or {}
            
            # Add basic file metadata
            if extract_metadata:
                file_metadata = {
                    "filename": document_path.name,
                    "file_path": str(document_path),
                    "file_type": file_extension,
                    "file_size": document_path.stat().st_size,
                    "document_id": str(uuid.uuid4())
                }
                doc_metadata.update(file_metadata)
            
            # Read the document based on file type
            if file_extension in ['.txt', '.md']:
                with open(document_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            elif file_extension == '.json':
                with open(document_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    # If it's a PGN in JSON format, handle it specially
                    if 'pgn' in json_data:
                        text = json_data['pgn']
                        # Extract additional metadata from JSON
                        if extract_metadata and 'metadata' in json_data:
                            doc_metadata.update(json_data['metadata'])
                    else:
                        # Generic JSON - convert to string
                        text = json.dumps(json_data, indent=2)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Chunk the text
            return self.chunk_text(text, doc_metadata)
            
        except Exception as e:
            self.logger.error(f"Error in chunk_document: {e}")
            raise

    def chunk_directory(self, directory_path: Union[str, Path], 
                      file_extensions: Optional[List[str]] = None,
                      recursive: bool = True,
                      metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Process all documents in a directory and split them into chunks.
        
        Args:
            directory_path: Path to the directory
            file_extensions: List of file extensions to process (e.g., ['.txt', '.md'])
            recursive: Whether to process subdirectories
            metadata: Optional metadata to attach to all chunks
            
        Returns:
            List of dictionaries containing chunks and their metadata
            
        Raises:
            FileNotFoundError: If the directory cannot be found
        """
        try:
            # Convert to Path if string
            if isinstance(directory_path, str):
                directory_path = Path(directory_path)
                
            # Check if directory exists
            if not directory_path.exists() or not directory_path.is_dir():
                raise FileNotFoundError(f"Directory not found: {directory_path}")
            
            # Default to common text file extensions
            if file_extensions is None:
                file_extensions = ['.txt', '.md', '.json']
                
            # Normalize extensions
            file_extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                             for ext in file_extensions]
            
            # Initialize result
            all_chunks = []
            
            # Function to process a single file
            def process_file(file_path):
                try:
                    file_chunks = self.chunk_document(file_path, metadata)
                    all_chunks.extend(file_chunks)
                    return len(file_chunks)
                except Exception as e:
                    self.logger.error(f"Error processing file {file_path}: {e}")
                    return 0
            
            # Find all files
            if recursive:
                files = [p for p in directory_path.glob('**/*') 
                       if p.is_file() and p.suffix.lower() in file_extensions]
            else:
                files = [p for p in directory_path.glob('*') 
                       if p.is_file() and p.suffix.lower() in file_extensions]
            
            # Process each file
            total_files = len(files)
            processed_files = 0
            total_chunks = 0
            
            for file_path in files:
                chunks_added = process_file(file_path)
                total_chunks += chunks_added
                processed_files += 1
                
                # Log progress periodically
                if processed_files % 10 == 0 or processed_files == total_files:
                    self.logger.info(f"Processed {processed_files}/{total_files} files, {total_chunks} chunks")
            
            return all_chunks
            
        except Exception as e:
            self.logger.error(f"Error in chunk_directory: {e}")
            raise

    def clean_chunk_text(self, text: str) -> str:
        """
        Clean and normalize chunk text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        try:
            # Basic cleaning operations
            # 1. Remove multiple spaces
            cleaned = re.sub(r'\s+', ' ', text)
            
            # 2. Remove multiple newlines
            cleaned = re.sub(r'\n+', '\n', cleaned)
            
            # 3. Strip whitespace from beginning and end
            cleaned = cleaned.strip()
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error in clean_chunk_text: {e}")
            return text  # Return original in case of error
    
    def add_hook(self, hook_type: str, hook_func: callable) -> None:
        """
        Add a processing hook function to the service.
        
        Args:
            hook_type: Type of hook ('pre_chunk', 'post_chunk')
            hook_func: Function to call
        """
        # Ensure hooks dict exists
        if not hasattr(self, 'hooks'):
            self.hooks = {
                'pre_chunk': [],
                'post_chunk': []
            }
            
        # Add the hook
        if hook_type in self.hooks:
            self.hooks[hook_type].append(hook_func)
            self.logger.info(f"Added {hook_type} hook: {hook_func.__name__}")
        else:
            raise ValueError(f"Unknown hook type: {hook_type}")
    
    def remove_hook(self, hook_type: str, hook_func: callable) -> bool:
        """
        Remove a processing hook function.
        
        Args:
            hook_type: Type of hook ('pre_chunk', 'post_chunk')
            hook_func: Function to remove
            
        Returns:
            True if the hook was removed, False if not found
        """
        # Check if hooks exist
        if not hasattr(self, 'hooks'):
            return False
            
        # Remove the hook
        if hook_type in self.hooks and hook_func in self.hooks[hook_type]:
            self.hooks[hook_type].remove(hook_func)
            self.logger.info(f"Removed {hook_type} hook: {hook_func.__name__}")
            return True
        
        return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # Create service instance
        service = ChunkingService(chunk_size=1000, chunk_overlap=200)
        logger.info("Chunking service initialized")
        
        # Test health check
        is_healthy = service.healthcheck()
        logger.info(f"Health check {'passed' if is_healthy else 'failed'}")
        
        # Example service usage
        sample_text = "This is a sample text that will be split into chunks. " * 50
        chunks = service.chunk_text(sample_text, {"source": "example"})
        logger.info(f"Created {len(chunks)} chunks from sample text")
        
        # Print the first chunk
        if chunks:
            logger.info(f"First chunk: {chunks[0]['text'][:100]}...")
            logger.info(f"Metadata: {chunks[0]['metadata']}")
        
    except Exception as e:
        logger.error(f"Error in Chunking service example: {e}", exc_info=True)