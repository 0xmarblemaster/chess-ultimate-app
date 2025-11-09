"""
Vector Store Service

Service for interacting with Weaviate vector database.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Union, Tuple
import uuid
import json
import time

# Weaviate client
import weaviate
from weaviate.util import generate_uuid5

# Import config
from backend.config import WEAVIATE_URL, WEAVIATE_API_KEY, WEAVIATE_GRPC_URL

logger = logging.getLogger(__name__)

class VectorStoreService:
    """
    Service for vector storage operations.
    
    This service handles:
    1. Connection to Weaviate vector database
    2. Creating and managing schemas
    3. Storing and retrieving vectors and data
    4. Performing vector similarity searches
    """
    
    def __init__(self, url=None, api_key=None, grpc_url=None):
        """
        Initialize the Vector Store service.
        
        Args:
            url: Weaviate instance URL (defaults to http://localhost:8080)
            api_key: API key for authentication (optional)
            grpc_url: gRPC URL for Weaviate (optional)
        """
        self.url = url or os.environ.get("WEAVIATE_URL", "http://localhost:8080")
        self.api_key = api_key or os.environ.get("WEAVIATE_API_KEY")
        self.grpc_url = grpc_url
        self.client = None
        self._is_connected = False
        self._connection_error = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Attempt initial connection
        try:
            self._connect()
        except Exception as e:
            self.logger.warning(f"Initial connection failed: {e}")
        
    def _connect(self) -> None:
        """
        Establish connection to Weaviate.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.logger.info(f"Connecting to Weaviate at {self.url}")
            
            # Setup authentication if API key is provided
            auth_config = weaviate.auth.AuthApiKey(api_key=self.api_key) if self.api_key else None
            
            # Create client using v3 API
            self.client = weaviate.Client(
                url=self.url,
                auth_client_secret=auth_config,
                additional_headers={
                    "X-OpenAI-Api-Key": os.environ.get("OPENAI_API_KEY", "")
                } if os.environ.get("OPENAI_API_KEY") else None,
                timeout_config=(5, 60)  # (connect_timeout, request_timeout)
            )
            
            # Test connection
            self.client.is_ready()
            self._is_connected = True
            self.logger.info(f"Connected to Weaviate at {self.url}")
            
        except Exception as e:
            self._is_connected = False
            self._connection_error = str(e)
            raise ConnectionError(f"Failed to connect to Weaviate at {self.url}: {e}")
    
    def healthcheck(self) -> bool:
        """
        Check if the service is operational.
        
        Returns:
            True if the service is healthy, False otherwise.
        """
        try:
            # If not connected, try to connect
            if not self._is_connected:
                try:
                    self._connect()
                except:
                    self.logger.error(f"Health check failed: Not connected to Weaviate. Error: {self._connection_error}")
                    return False
            
            # Check if Weaviate is ready
            is_ready = self.client.is_ready()
            if not is_ready:
                self.logger.error("Health check failed: Weaviate is not ready")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def ensure_schema(self, class_name: str, class_config: Dict[str, Any]) -> bool:
        """
        Create a schema class if it doesn't exist.
        
        Args:
            class_name: Name of the class to create
            class_config: Configuration for the class
            
        Returns:
            True if schema is ready, False otherwise
        """
        try:
            # Check connection
            if not self._is_connected:
                self._connect()
            
            # Check if class already exists
            if self.client.schema.exists(class_name):
                self.logger.info(f"Schema class {class_name} already exists")
                return True
            
            # Create class
            self.client.schema.create_class(class_config)
            self.logger.info(f"Created schema class {class_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating schema class {class_name}: {e}")
            return False
    
    def store_chunks(self, chunks: List[Dict[str, Any]], 
                   class_name: str, 
                   batch_size: int = 50,
                   with_vector: bool = False) -> Tuple[int, List[str]]:
        """
        Store text chunks in Weaviate.
        
        Args:
            chunks: List of chunk dictionaries with text and metadata
            class_name: Name of the Weaviate class to store in
            batch_size: Number of objects to batch in one request
            with_vector: Whether chunks already have vectors
            
        Returns:
            Tuple of (number of chunks stored, list of IDs)
            
        Raises:
            ConnectionError: If not connected to Weaviate
            ValueError: If chunks are invalid
        """
        try:
            # Check connection
            if not self._is_connected:
                self._connect()
            
            # Check if chunks is valid
            if not chunks or not isinstance(chunks, list):
                raise ValueError("Invalid chunks: must be a non-empty list")
            
            # Ensure the class exists
            if not self.client.schema.exists(class_name):
                raise ValueError(f"Schema class {class_name} does not exist")
            
            # Prepare batch process
            with self.client.batch as batch:
                # Configure batch
                batch.batch_size = batch_size
                batch.dynamic = True  # Automatically determine batch size
                
                stored_ids = []
                
                # Add data objects to batch
                for i, chunk in enumerate(chunks):
                    # Extract text and metadata
                    if "text" not in chunk:
                        self.logger.warning(f"Skipping chunk {i} without text field")
                        continue
                        
                    text = chunk["text"]
                    metadata = chunk.get("metadata", {})
                    
                    # Generate a deterministic UUID if chunk_id exists in metadata
                    if "chunk_id" in metadata:
                        object_uuid = generate_uuid5(metadata["chunk_id"])
                    else:
                        object_uuid = None  # Weaviate will generate a random UUID
                    
                    # Create properties object
                    properties = {
                        "content": text,
                        **metadata
                    }
                    
                    # Add with vector if provided
                    if with_vector and "vector" in chunk:
                        batch.add_data_object(
                            properties,
                            class_name,
                            uuid=object_uuid,
                            vector=chunk["vector"]
                        )
                    else:
                        batch.add_data_object(
                            properties,
                            class_name,
                            uuid=object_uuid
                        )
                    
                    # Track stored ID
                    stored_ids.append(str(object_uuid) if object_uuid else f"chunk_{i}")
            
            # Return count and IDs
            return len(stored_ids), stored_ids
            
        except Exception as e:
            self.logger.error(f"Error storing chunks: {e}")
            raise
    
    def query(self, query_text: str, 
             class_name: str, 
             limit: int = 10, 
             filter_terms: Optional[Dict[str, Any]] = None,
             include_vector: bool = False) -> List[Dict[str, Any]]:
        """
        Perform a semantic search query against Weaviate.
        
        Args:
            query_text: The search query text
            class_name: The class to search in
            limit: Maximum number of results to return
            filter_terms: Optional dictionary of filter terms
            include_vector: Whether to include the vector in the response
            
        Returns:
            List of matching objects with their properties
            
        Raises:
            ConnectionError: If not connected to Weaviate
            ValueError: If the query is invalid
        """
        try:
            # Check connection
            if not self._is_connected:
                self._connect()
            
            # Validate query
            if not query_text or not class_name:
                raise ValueError("Query text and class name must be provided")
            
            # Prepare query builder
            query_builder = (
                self.client.query
                .get(class_name, ["content", "_additional {certainty distance}"])
                .with_limit(limit)
                .with_near_text({"concepts": [query_text]})
            )
            
            # Add filters if provided
            if filter_terms:
                where_filter = self._build_where_filter(filter_terms)
                if where_filter:
                    query_builder = query_builder.with_where(where_filter)
            
            # Add vector if requested
            if include_vector:
                query_builder = query_builder.with_additional(["vector"])
            
            # Execute the query
            result = query_builder.do()
            
            # Extract and process results
            if not result or f"Get{class_name}" not in result:
                return []
                
            entries = result[f"Get{class_name}"]
            
            # Format results
            formatted_results = []
            for entry in entries:
                # Get certainty score
                certainty = None
                distance = None
                if "_additional" in entry:
                    certainty = entry["_additional"].get("certainty")
                    distance = entry["_additional"].get("distance")
                
                # Build result object
                result_obj = {
                    "content": entry.get("content", ""),
                    "certainty": certainty,
                    "distance": distance,
                }
                
                # Add vector if included
                if include_vector and "_additional" in entry and "vector" in entry["_additional"]:
                    result_obj["vector"] = entry["_additional"]["vector"]
                
                # Add other properties (metadata)
                for key, value in entry.items():
                    if key not in ["content", "_additional"]:
                        result_obj[key] = value
                
                formatted_results.append(result_obj)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error in query: {e}")
            raise
    
    def _build_where_filter(self, filter_terms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a Weaviate where filter from filter terms.
        
        Args:
            filter_terms: Dictionary of filter terms
            
        Returns:
            Weaviate where filter object
        """
        if not filter_terms:
            return {}
            
        # Simple filter conversion - for complex filters, this would need to be expanded
        filter_obj = {}
        
        for key, value in filter_terms.items():
            if isinstance(value, list):
                # Handle list values (OR condition)
                operands = [{"path": [key], "operator": "Equal", "valueText": str(v)} for v in value]
                filter_obj = {"operator": "Or", "operands": operands}
            else:
                # Handle single values
                filter_obj = {"path": [key], "operator": "Equal", "valueText": str(value)}
        
        return filter_obj
    
    def delete_by_filter(self, class_name: str, filter_terms: Dict[str, Any]) -> int:
        """
        Delete objects that match the given filter.
        
        Args:
            class_name: The class to delete from
            filter_terms: Dictionary of filter terms
            
        Returns:
            Number of objects deleted
            
        Raises:
            ConnectionError: If not connected to Weaviate
        """
        try:
            # Check connection
            if not self._is_connected:
                self._connect()
            
            # Build where filter
            where_filter = self._build_where_filter(filter_terms)
            if not where_filter:
                return 0
            
            # Get matching objects to count them
            query = (
                self.client.query
                .get(class_name, ["_additional {id}"])
                .with_where(where_filter)
                .do()
            )
            
            # Extract object IDs
            object_count = 0
            if query and f"Get{class_name}" in query:
                object_count = len(query[f"Get{class_name}"])
            
            # Delete objects
            self.client.batch.delete_objects(
                class_name=class_name,
                where=where_filter
            )
            
            self.logger.info(f"Deleted {object_count} objects from {class_name}")
            return object_count
            
        except Exception as e:
            self.logger.error(f"Error in delete_by_filter: {e}")
            raise
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the current Weaviate schema.
        
        Returns:
            Dictionary of schema classes and their configuration
        """
        try:
            # Check connection
            if not self._is_connected:
                self._connect()
                
            # Get schema
            return self.client.schema.get()
            
        except Exception as e:
            self.logger.error(f"Error getting schema: {e}")
            raise
    
    def count_objects(self, class_name: str, filter_terms: Optional[Dict[str, Any]] = None) -> int:
        """
        Count the number of objects in a class, optionally filtered.
        
        Args:
            class_name: The class to count in
            filter_terms: Optional dictionary of filter terms
            
        Returns:
            Number of objects in the class
        """
        try:
            # Check connection
            if not self._is_connected:
                self._connect()
            
            # Build aggregate query
            if filter_terms:
                where_filter = self._build_where_filter(filter_terms)
                result = (
                    self.client.query
                    .aggregate(class_name)
                    .with_where(where_filter)
                    .with_meta_count()
                    .do()
                )
            else:
                result = (
                    self.client.query
                    .aggregate(class_name)
                    .with_meta_count()
                    .do()
                )
            
            # Extract count
            if result and f"Aggregate{class_name}" in result:
                agg = result[f"Aggregate{class_name}"]
                if agg and len(agg) > 0 and "meta" in agg[0]:
                    return agg[0]["meta"]["count"]
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Error in count_objects: {e}")
            # Return 0 instead of raising to make it easier to use
            return 0


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # Create service instance
        service = VectorStoreService()
        logger.info("Vector Store service initialized")
        
        # Test health check
        is_healthy = service.healthcheck()
        logger.info(f"Health check {'passed' if is_healthy else 'failed'}")
        
        if is_healthy:
            # Get schema
            schema = service.get_schema()
            logger.info(f"Schema has {len(schema['classes'])} classes")
            
            # Example class creation
            class_exists = service.ensure_schema("ChessExample", {
                "class": "ChessExample",
                "description": "Sample class for testing",
                "vectorizer": "text2vec-openai",
                "properties": [
                    {
                        "name": "content",
                        "description": "The text content",
                        "dataType": ["text"]
                    },
                    {
                        "name": "source",
                        "description": "Source of the content",
                        "dataType": ["string"]
                    }
                ]
            })
            
            if class_exists:
                # Example data storage
                chunks = [
                    {
                        "text": "The Sicilian Defense is a chess opening that begins with the moves 1.e4 c5.",
                        "metadata": {"source": "example", "topic": "openings"}
                    },
                    {
                        "text": "The Ruy Lopez is a chess opening characterized by the moves 1.e4 e5 2.Nf3 Nc6 3.Bb5.",
                        "metadata": {"source": "example", "topic": "openings"}
                    }
                ]
                
                count, ids = service.store_chunks(chunks, "ChessExample")
                logger.info(f"Stored {count} chunks with IDs: {ids}")
                
                # Example query
                results = service.query("Sicilian Defense", "ChessExample")
                if results:
                    logger.info(f"Query returned {len(results)} results")
                    logger.info(f"Top result: {results[0]['content']}")
                    logger.info(f"Certainty: {results[0]['certainty']}")
        
    except Exception as e:
        logger.error(f"Error in Vector Store service example: {e}", exc_info=True)