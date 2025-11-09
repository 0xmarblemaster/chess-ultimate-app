"""
Lesson Repository

Repository for storing and retrieving chess lesson data.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import json
import os
import uuid

# Import services
from backend.services.vector_store_service import VectorStoreService

# Import configuration
from backend import config

logger = logging.getLogger(__name__)

class LessonRepository:
    """
    Repository for chess lesson data.
    
    This repository is responsible for:
    - Storing lesson chunks
    - Retrieving lessons by various criteria
    - Searching lesson content
    - Managing lesson metadata and relationships
    """
    
    def __init__(self, 
                 vector_store: Optional[VectorStoreService] = None, 
                 collection_name: str = None):
        """
        Initialize the Lesson Repository.
        
        Args:
            vector_store: Vector store service instance
            collection_name: Collection name for lessons in vector store
        """
        self.logger = logger
        self.vector_store = vector_store or VectorStoreService()
        self.collection_name = collection_name or getattr(config, 'WEAVIATE_CLASS_NAME', "ChessLessonChunk")
        
        # Ensure the collection schema exists
        self._ensure_schema_exists()
    
    def _ensure_schema_exists(self) -> bool:
        """
        Ensure the lesson collection schema exists in the vector store.
        
        Returns:
            True if schema exists or was created successfully
        """
        try:
            # Check if the collection exists
            if not self.vector_store.client.schema.exists(self.collection_name):
                # Create the schema
                schema = {
                    "classes": [
                        {
                            "class": self.collection_name,
                            "description": "Chess lesson chunks with metadata",
                            "vectorizer": "text2vec-openai",  # or other configured vectorizer
                            "properties": [
                                {
                                    "name": "content",
                                    "dataType": ["text"],
                                    "description": "The text content of the lesson chunk"
                                },
                                {
                                    "name": "chunkId",
                                    "dataType": ["string"],
                                    "description": "Unique ID for this chunk"
                                },
                                {
                                    "name": "book",
                                    "dataType": ["string"],
                                    "description": "Title of the book or source"
                                },
                                {
                                    "name": "lessonNumber",
                                    "dataType": ["int"],
                                    "description": "Lesson number within the book"
                                },
                                {
                                    "name": "lessonTitle",
                                    "dataType": ["string"],
                                    "description": "Title of the lesson"
                                },
                                {
                                    "name": "chunkType",
                                    "dataType": ["string"],
                                    "description": "Type of chunk (e.g., 'explanation', 'task', 'example')"
                                },
                                {
                                    "name": "diagramReference",
                                    "dataType": ["string"],
                                    "description": "Reference to a diagram image if any"
                                },
                                {
                                    "name": "diagramNumber",
                                    "dataType": ["int"],
                                    "description": "Number of the diagram if any"
                                },
                                {
                                    "name": "fen",
                                    "dataType": ["string"],
                                    "description": "FEN string for the position if any"
                                },
                                {
                                    "name": "pgn",
                                    "dataType": ["string"],
                                    "description": "PGN notation for moves if any"
                                },
                                {
                                    "name": "difficulty",
                                    "dataType": ["string"],
                                    "description": "Difficulty level of the chunk"
                                },
                                {
                                    "name": "tags",
                                    "dataType": ["string[]"],
                                    "description": "Tags describing the content"
                                },
                                {
                                    "name": "topics",
                                    "dataType": ["string[]"],
                                    "description": "Chess topics covered in the chunk"
                                },
                                {
                                    "name": "source",
                                    "dataType": ["string"],
                                    "description": "Source file of the lesson"
                                },
                                {
                                    "name": "sourceType",
                                    "dataType": ["string"],
                                    "description": "Type of source (e.g., 'pdf', 'docx')"
                                }
                            ]
                        }
                    ]
                }
                
                # Create the schema class
                self.vector_store.client.schema.create_class(schema["classes"][0])
                self.logger.info(f"Created schema for {self.collection_name}")
                return True
            return True
        except Exception as e:
            self.logger.error(f"Error ensuring schema exists for {self.collection_name}: {e}")
            return False
    
    def store_chunk(self, chunk_data: Dict[str, Any]) -> Optional[str]:
        """
        Store a single lesson chunk.
        
        Args:
            chunk_data: Chunk data to store
            
        Returns:
            ID of the stored chunk or None if failed
        """
        try:
            # Validate required fields
            required_fields = ["content", "book"]
            for field in required_fields:
                if field not in chunk_data:
                    self.logger.warning(f"Chunk data missing required field: {field}")
                    return None
            
            # Ensure chunk has an ID
            if "chunkId" not in chunk_data:
                chunk_data["chunkId"] = str(uuid.uuid4())
            
            # Store in vector db
            with self.vector_store.client.batch as batch:
                uuid_str = batch.add_data_object(
                    data_object=chunk_data,
                    class_name=self.collection_name
                )
                
            self.logger.info(f"Stored chunk: {chunk_data['chunkId']} from {chunk_data['book']}")
            return uuid_str
        except Exception as e:
            self.logger.error(f"Error storing chunk: {e}")
            return None
    
    def store_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """
        Store multiple lesson chunks.
        
        Args:
            chunks: List of chunk data objects
            
        Returns:
            Tuple of (number of chunks stored, list of IDs)
        """
        try:
            if not chunks:
                return 0, []
                
            # Use the vector store service's store_chunks method
            count, ids = self.vector_store.store_chunks(
                chunks=chunks,
                class_name=self.collection_name
            )
            
            self.logger.info(f"Stored {count} chunks")
            return count, ids
        except Exception as e:
            self.logger.error(f"Error storing chunks: {e}")
            return 0, []
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a chunk by its ID.
        
        Args:
            chunk_id: ID of the chunk
            
        Returns:
            Chunk data or None if not found
        """
        try:
            # First try to get by UUID
            try:
                result = self.vector_store.client.data_object.get_by_id(
                    uuid=chunk_id,
                    class_name=self.collection_name
                )
                
                if result:
                    return result
            except:
                pass
                
            # If not found, try to get by chunkId field
            where_filter = {
                "path": ["chunkId"],
                "operator": "Equal",
                "valueString": chunk_id
            }
            
            result = (
                self.vector_store.client.query
                .get(self.collection_name)
                .with_where(where_filter)
                .with_limit(1)
                .do()
            )
            
            # Extract and return chunk
            chunks = result.get(f"Get{self.collection_name}", [])
            
            if not chunks:
                return None
                
            return chunks[0]
        except Exception as e:
            self.logger.error(f"Error getting chunk by ID: {e}")
            return None
    
    def search_lessons(self, query: str, limit: int = 10, 
                    filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for lesson chunks using semantic search.
        
        Args:
            query: Search query (e.g., "queen endgames", "pawn structure")
            limit: Maximum number of results to return
            filters: Optional filters (e.g., {"book": "Chess Strategy", "lessonNumber": 5})
            
        Returns:
            List of matching chunk objects
        """
        try:
            # Use the vector store service's query method
            results = self.vector_store.query(
                query_text=query,
                class_name=self.collection_name,
                limit=limit,
                filter_terms=filters
            )
            
            self.logger.info(f"Search for '{query}' returned {len(results)} results")
            return results
        except Exception as e:
            self.logger.error(f"Error searching lessons: {e}")
            return []
    
    def get_lessons_by_book(self, book_title: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific book.
        
        Args:
            book_title: Title of the book
            
        Returns:
            List of chunk objects
        """
        try:
            # Build where filter
            where_filter = {
                "path": ["book"],
                "operator": "Equal",
                "valueString": book_title
            }
            
            # Run query
            result = (
                self.vector_store.client.query
                .get(self.collection_name)
                .with_where(where_filter)
                .with_limit(1000)  # Large limit to get all chunks
                .do()
            )
            
            # Extract and return chunks
            chunks = result.get(f"Get{self.collection_name}", [])
            
            self.logger.info(f"Found {len(chunks)} chunks for book '{book_title}'")
            return chunks
        except Exception as e:
            self.logger.error(f"Error getting lessons by book: {e}")
            return []
    
    def get_lesson_by_number(self, book_title: str, lesson_number: int) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific lesson by its number.
        
        Args:
            book_title: Title of the book
            lesson_number: Number of the lesson
            
        Returns:
            List of chunk objects
        """
        try:
            # Build where filter
            where_filter = {
                "operator": "And",
                "operands": [
                    {
                        "path": ["book"],
                        "operator": "Equal",
                        "valueString": book_title
                    },
                    {
                        "path": ["lessonNumber"],
                        "operator": "Equal",
                        "valueNumber": lesson_number
                    }
                ]
            }
            
            # Run query
            result = (
                self.vector_store.client.query
                .get(self.collection_name)
                .with_where(where_filter)
                .with_limit(200)  # Reasonable limit for a single lesson
                .do()
            )
            
            # Extract and return chunks
            chunks = result.get(f"Get{self.collection_name}", [])
            
            self.logger.info(f"Found {len(chunks)} chunks for lesson {lesson_number} in book '{book_title}'")
            return chunks
        except Exception as e:
            self.logger.error(f"Error getting lesson by number: {e}")
            return []
    
    def get_chunks_by_type(self, chunk_type: str, limit: int = 100, 
                        filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get chunks by their type with optional additional filters.
        
        Args:
            chunk_type: Type of chunks to retrieve (e.g., 'task', 'explanation')
            limit: Maximum number of results to return
            filters: Additional filter criteria
            
        Returns:
            List of matching chunk objects
        """
        try:
            # Build where filter
            filter_parts = [
                {
                    "path": ["chunkType"],
                    "operator": "Equal",
                    "valueString": chunk_type
                }
            ]
            
            # Add additional filters if provided
            if filters:
                for key, value in filters.items():
                    if isinstance(value, str):
                        filter_parts.append({
                            "path": [key],
                            "operator": "Equal",
                            "valueString": value
                        })
                    elif isinstance(value, (int, float)):
                        filter_parts.append({
                            "path": [key],
                            "operator": "Equal",
                            "valueNumber": value
                        })
            
            # Combine filters with AND
            where_filter = filter_parts[0] if len(filter_parts) == 1 else {
                "operator": "And",
                "operands": filter_parts
            }
            
            # Run query
            result = (
                self.vector_store.client.query
                .get(self.collection_name)
                .with_where(where_filter)
                .with_limit(limit)
                .do()
            )
            
            # Extract and return chunks
            chunks = result.get(f"Get{self.collection_name}", [])
            
            self.logger.info(f"Found {len(chunks)} chunks of type '{chunk_type}'")
            return chunks
        except Exception as e:
            self.logger.error(f"Error getting chunks by type: {e}")
            return []
    
    def get_tasks_with_diagrams(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get task chunks that have diagram references.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of task chunks with diagrams
        """
        try:
            # Build where filter - tasks with non-null diagram references
            where_filter = {
                "operator": "And",
                "operands": [
                    {
                        "path": ["chunkType"],
                        "operator": "Equal",
                        "valueString": "task"
                    },
                    {
                        "path": ["diagramReference"],
                        "operator": "NotEqual",
                        "valueString": ""  # Look for non-empty diagram reference
                    }
                ]
            }
            
            # Run query
            result = (
                self.vector_store.client.query
                .get(self.collection_name)
                .with_where(where_filter)
                .with_limit(limit)
                .do()
            )
            
            # Extract and return chunks
            chunks = result.get(f"Get{self.collection_name}", [])
            
            self.logger.info(f"Found {len(chunks)} task chunks with diagrams")
            return chunks
        except Exception as e:
            self.logger.error(f"Error getting tasks with diagrams: {e}")
            return []
    
    def healthcheck(self) -> bool:
        """
        Perform a health check on the repository.
        
        Returns:
            True if repository is healthy
        """
        try:
            # Check if vector store exists and is properly initialized
            if not self.vector_store:
                self.logger.warning("Vector store service is None")
                return False
                
            if not hasattr(self.vector_store, 'client') or not self.vector_store.client:
                self.logger.warning("Vector store client is None")
                return False
            
            # Check vector store connection
            if hasattr(self.vector_store, '_is_connected') and not self.vector_store._is_connected:
                try:
                    self.vector_store._connect()
                except Exception as e:
                    self.logger.warning(f"Failed to connect to vector store: {e}")
                    return False
                
            # Check if collection exists
            if not self.vector_store.client.schema.exists(self.collection_name):
                self.logger.warning(f"Collection {self.collection_name} does not exist")
                return False
                
            # Try a simple query
            self.vector_store.client.query.get(
                class_name=self.collection_name,
                properties=["chunkId", "book"]
            ).with_limit(1).do()
            
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    repo = LessonRepository()
    
    if repo.healthcheck():
        print("LessonRepository is healthy!")
        
        # Example: Store a sample chunk
        sample_chunk = {
            "content": "The queen endgame is one of the most important endgames to master. In most cases, the side with the queen wins against a rook, but there are important defensive techniques.",
            "book": "Endgame Strategy",
            "lessonNumber": 8,
            "lessonTitle": "Queen vs Rook Endgames",
            "chunkType": "explanation",
            "tags": ["endgame", "queen", "rook"],
            "topics": ["queen endgame", "defensive techniques"],
            "source": "endgames.pdf",
            "sourceType": "pdf"
        }
        
        chunk_id = repo.store_chunk(sample_chunk)
        if chunk_id:
            print(f"Stored sample chunk with ID: {chunk_id}")
            
            # Example: Search chunks
            results = repo.search_lessons("queen vs rook endgame")
            if results:
                print(f"Found {len(results)} chunks, top match: '{results[0]['content'][:100]}...'")
            else:
                print("No chunks found in search")
    else:
        print("LessonRepository health check failed!") 