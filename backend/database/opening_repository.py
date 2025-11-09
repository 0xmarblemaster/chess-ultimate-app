"""
Opening Repository

Repository for storing and retrieving chess opening data.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import json
import os

# Import services
from backend.services.vector_store_service import VectorStoreService

# Import configuration
from backend import config

logger = logging.getLogger(__name__)

class OpeningRepository:
    """
    Repository for chess opening data.
    
    This repository is responsible for:
    - Storing opening information (ECO codes, names, variations)
    - Retrieving opening data by various criteria
    - Searching opening data
    - Managing opening metadata and relationships
    """
    
    def __init__(self, 
                 vector_store: Optional[VectorStoreService] = None, 
                 collection_name: str = None):
        """
        Initialize the Opening Repository.
        
        Args:
            vector_store: Vector store service instance
            collection_name: Collection name for openings in vector store
        """
        self.logger = logger
        self.vector_store = vector_store or VectorStoreService()
        self.collection_name = collection_name or getattr(config, 'WEAVIATE_OPENINGS_CLASS_NAME', "ChessOpening")
        
        # Ensure the collection schema exists
        self._ensure_schema_exists()
    
    def _ensure_schema_exists(self) -> bool:
        """
        Ensure the opening collection schema exists in the vector store.
        
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
                            "description": "Chess opening information and variations",
                            "vectorizer": "text2vec-openai",  # or other configured vectorizer
                            "properties": [
                                {
                                    "name": "eco",
                                    "dataType": ["string"],
                                    "description": "ECO code for the opening (e.g., 'B01')"
                                },
                                {
                                    "name": "name",
                                    "dataType": ["string"],
                                    "description": "Name of the opening"
                                },
                                {
                                    "name": "pgn",
                                    "dataType": ["text"],
                                    "description": "PGN notation for the opening moves"
                                },
                                {
                                    "name": "moves",
                                    "dataType": ["string"],
                                    "description": "Opening moves in SAN notation"
                                },
                                {
                                    "name": "fen",
                                    "dataType": ["string"],
                                    "description": "FEN string for the position after the opening moves"
                                },
                                {
                                    "name": "category",
                                    "dataType": ["string"],
                                    "description": "Category of the opening (e.g., 'Open Game', 'Semi-Open')"
                                },
                                {
                                    "name": "description",
                                    "dataType": ["text"],
                                    "description": "Description of the opening and its key ideas"
                                },
                                {
                                    "name": "parentEco",
                                    "dataType": ["string"],
                                    "description": "ECO code of the parent opening (if this is a variation)"
                                },
                                {
                                    "name": "variations",
                                    "dataType": ["string[]"],
                                    "description": "ECO codes of known variations of this opening"
                                },
                                {
                                    "name": "popularity",
                                    "dataType": ["number"],
                                    "description": "Relative popularity of the opening (0-100)"
                                },
                                {
                                    "name": "evaluation",
                                    "dataType": ["number"],
                                    "description": "Approximate engine evaluation of the position"
                                },
                                {
                                    "name": "tags",
                                    "dataType": ["string[]"],
                                    "description": "Tags describing the opening (e.g., 'tactical', 'positional')"
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
    
    def store_opening(self, opening_data: Dict[str, Any]) -> Optional[str]:
        """
        Store a single opening.
        
        Args:
            opening_data: Opening data to store
            
        Returns:
            ID of the stored opening or None if failed
        """
        try:
            # Validate required fields
            required_fields = ["eco", "name", "moves"]
            for field in required_fields:
                if field not in opening_data:
                    self.logger.warning(f"Opening data missing required field: {field}")
                    return None
            
            # Store in vector db
            with self.vector_store.client.batch as batch:
                uuid = batch.add_data_object(
                    data_object=opening_data,
                    class_name=self.collection_name
                )
                
            self.logger.info(f"Stored opening: {opening_data['name']} ({opening_data['eco']})")
            return uuid
        except Exception as e:
            self.logger.error(f"Error storing opening: {e}")
            return None
    
    def store_openings_from_file(self, file_path: str) -> Tuple[int, int]:
        """
        Import openings from a JSON file.
        
        Args:
            file_path: Path to JSON file with opening data
            
        Returns:
            Tuple of (total openings, successfully stored openings)
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Openings file not found: {file_path}")
                return 0, 0
            
            # Read openings file
            with open(file_path, 'r', encoding='utf-8') as f:
                openings = json.load(f)
            
            total_count = len(openings)
            success_count = 0
            
            # Store in batches of 50
            batch_objects = []
            
            for opening in openings:
                batch_objects.append(opening)
                
                if len(batch_objects) >= 50:
                    success_count += self._store_batch(batch_objects)
                    batch_objects = []
            
            # Store any remaining openings
            if batch_objects:
                success_count += self._store_batch(batch_objects)
            
            self.logger.info(f"Imported {success_count}/{total_count} openings")
            return total_count, success_count
        except Exception as e:
            self.logger.error(f"Error importing openings: {e}")
            return 0, 0
    
    def _store_batch(self, openings: List[Dict[str, Any]]) -> int:
        """
        Store a batch of openings.
        
        Args:
            openings: List of opening data objects
            
        Returns:
            Number of successfully stored openings
        """
        success_count = 0
        try:
            with self.vector_store.client.batch as batch:
                for opening in openings:
                    # Validate required fields
                    if all(field in opening for field in ["eco", "name", "moves"]):
                        batch.add_data_object(
                            data_object=opening,
                            class_name=self.collection_name
                        )
                        success_count += 1
                    else:
                        self.logger.warning(f"Skipping opening with missing required fields: {opening.get('eco', 'unknown')}")
            return success_count
        except Exception as e:
            self.logger.error(f"Error storing batch: {e}")
            return success_count
    
    def get_opening_by_eco(self, eco_code: str) -> Optional[Dict[str, Any]]:
        """
        Get opening by ECO code.
        
        Args:
            eco_code: ECO code of the opening
            
        Returns:
            Opening data or None if not found
        """
        try:
            # Build where filter
            where_filter = {
                "path": ["eco"],
                "operator": "Equal",
                "valueString": eco_code
            }
            
            # Run query
            result = (
                self.vector_store.client.query
                .get(self.collection_name, ["eco", "name", "moves", "pgn", "fen", "description", "category", "popularity", "evaluation", "tags"])
                .with_where(where_filter)
                .with_limit(1)
                .do()
            )
            
            # Extract and return opening
            openings = result.get(f"Get{self.collection_name}", [])
            
            if not openings:
                return None
                
            return openings[0]
        except Exception as e:
            self.logger.error(f"Error getting opening by ECO code: {e}")
            return None
    
    def get_opening_by_moves(self, moves: str) -> Optional[Dict[str, Any]]:
        """
        Get opening by move sequence.
        
        Args:
            moves: Opening moves in SAN notation
            
        Returns:
            Opening data or None if not found
        """
        try:
            # Build where filter
            where_filter = {
                "path": ["moves"],
                "operator": "Equal",
                "valueString": moves
            }
            
            # Run query
            result = (
                self.vector_store.client.query
                .get(self.collection_name, ["eco", "name", "moves", "pgn", "fen", "description", "category", "popularity", "evaluation", "tags"])
                .with_where(where_filter)
                .with_limit(1)
                .do()
            )
            
            # Extract and return opening
            openings = result.get(f"Get{self.collection_name}", [])
            
            if not openings:
                return None
                
            return openings[0]
        except Exception as e:
            self.logger.error(f"Error getting opening by moves: {e}")
            return None
    
    def search_openings(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for openings using semantic search.
        
        Args:
            query: Search query (e.g., "Sicilian Defense", "e4 e5 Nf3")
            limit: Maximum number of results to return
            
        Returns:
            List of matching opening data objects
        """
        try:
            # Perform vector search
            results = self.vector_store.query(
                query_text=query,
                class_name=self.collection_name,
                limit=limit
            )
            
            self.logger.info(f"Search for '{query}' returned {len(results)} results")
            return results
        except Exception as e:
            self.logger.error(f"Error searching openings: {e}")
            return []
    
    def filter_openings(self, 
                      category: Optional[str] = None, 
                      min_popularity: Optional[float] = None,
                      tags: Optional[List[str]] = None,
                      limit: int = 20) -> List[Dict[str, Any]]:
        """
        Filter openings by category, popularity, and/or tags.
        
        Args:
            category: Opening category
            min_popularity: Minimum popularity score
            tags: List of tags to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of matching opening data objects
        """
        try:
            # Build where filter
            filter_parts = []
            
            if category:
                filter_parts.append({
                    "path": ["category"],
                    "operator": "Equal",
                    "valueString": category
                })
            
            if min_popularity is not None:
                filter_parts.append({
                    "path": ["popularity"],
                    "operator": "GreaterThanEqual",
                    "valueNumber": min_popularity
                })
            
            if tags:
                # For each tag, check if it's in the tags array
                tag_filters = []
                for tag in tags:
                    tag_filters.append({
                        "path": ["tags"],
                        "operator": "ContainsAny",
                        "valueString": tag
                    })
                
                # Combine tag filters with OR
                if len(tag_filters) == 1:
                    filter_parts.append(tag_filters[0])
                else:
                    filter_parts.append({
                        "operator": "Or",
                        "operands": tag_filters
                    })
            
            # Combine all filters with AND
            where_filter = None
            if len(filter_parts) == 1:
                where_filter = filter_parts[0]
            elif len(filter_parts) > 1:
                where_filter = {
                    "operator": "And",
                    "operands": filter_parts
                }
            
            # If no filters, return empty list
            if not where_filter:
                return []
            
            # Run query
            result = (
                self.vector_store.client.query
                .get(self.collection_name, ["eco", "name", "moves", "pgn", "fen", "description", "category", "popularity", "evaluation", "tags"])
                .with_where(where_filter)
                .with_limit(limit)
                .do()
            )
            
            # Extract and return openings
            openings = result.get(f"Get{self.collection_name}", [])
            
            self.logger.info(f"Filter returned {len(openings)} openings")
            return openings
        except Exception as e:
            self.logger.error(f"Error filtering openings: {e}")
            return []
    
    def healthcheck(self) -> bool:
        """
        Perform a health check on the repository.
        
        Returns:
            True if repository is healthy
        """
        try:
            # Check vector store connection
            if not self.vector_store._is_connected:
                self.vector_store._connect()
                
            # Check if collection exists
            if not self.vector_store.client.schema.exists(self.collection_name):
                self.logger.warning(f"Collection {self.collection_name} does not exist")
                return False
                
            # Try a simple query
            self.vector_store.client.query.get(
                class_name=self.collection_name,
                properties=["eco", "name"]
            ).with_limit(1).do()
            
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    repo = OpeningRepository()
    
    if repo.healthcheck():
        print("OpeningRepository is healthy!")
        
        # Example: Store a sample opening
        sicilian = {
            "eco": "B20",
            "name": "Sicilian Defense",
            "pgn": "1. e4 c5",
            "moves": "e4 c5",
            "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "category": "Semi-Open Game",
            "description": "The Sicilian Defense is the most popular response to White's opening 1.e4. Black immediately fights for the center but from the flank, which leads to unbalanced positions.",
            "popularity": 90,
            "evaluation": 0.2,
            "tags": ["aggressive", "complex", "tactical"]
        }
        
        opening_id = repo.store_opening(sicilian)
        if opening_id:
            print(f"Stored Sicilian Defense with ID: {opening_id}")
            
            # Example: Search openings
            results = repo.search_openings("sicilian")
            if results:
                print(f"Found {len(results)} openings, top match: {results[0]['name']} ({results[0]['eco']})")
            else:
                print("No openings found in search")
    else:
        print("OpeningRepository health check failed!") 