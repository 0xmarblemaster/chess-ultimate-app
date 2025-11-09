"""
Game Repository

Repository for storing and retrieving chess game data.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import os
import chess.pgn
import io
import json
import datetime

# Import services
from backend.services.vector_store_service import VectorStoreService

# Import configuration
from backend import config

logger = logging.getLogger(__name__)

class GameRepository:
    """
    Repository for chess game data.
    
    This repository is responsible for:
    - Storing PGN game data
    - Retrieving game data by various criteria
    - Searching game data
    - Maintaining game metadata
    """
    
    def __init__(self, 
                 vector_store: Optional[VectorStoreService] = None, 
                 collection_name: str = None):
        """
        Initialize the Game Repository.
        
        Args:
            vector_store: Vector store service instance
            collection_name: Collection name for games in vector store
        """
        self.logger = logger
        self.vector_store = vector_store or VectorStoreService()
        self.collection_name = collection_name or getattr(config, 'WEAVIATE_GAMES_CLASS_NAME', "ChessGame")
        
        # Ensure the collection schema exists
        self._ensure_schema_exists()
    
    def _ensure_schema_exists(self) -> bool:
        """
        Ensure the game collection schema exists in the vector store.
        
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
                            "description": "Chess game records with metadata",
                            "vectorizer": "text2vec-openai",  # or other configured vectorizer
                            "properties": [
                                {
                                    "name": "pgn",
                                    "dataType": ["text"],
                                    "description": "Full PGN text of the game"
                                },
                                {
                                    "name": "white",
                                    "dataType": ["string"],
                                    "description": "Name of the white player"
                                },
                                {
                                    "name": "black",
                                    "dataType": ["string"],
                                    "description": "Name of the black player"
                                },
                                {
                                    "name": "date",
                                    "dataType": ["date"],
                                    "description": "Date the game was played"
                                },
                                {
                                    "name": "result",
                                    "dataType": ["string"],
                                    "description": "Game result (e.g., '1-0', '0-1', '1/2-1/2')"
                                },
                                {
                                    "name": "eco",
                                    "dataType": ["string"],
                                    "description": "ECO code for the opening"
                                },
                                {
                                    "name": "event",
                                    "dataType": ["string"],
                                    "description": "Name of the tournament or event"
                                },
                                {
                                    "name": "site",
                                    "dataType": ["string"],
                                    "description": "Location where the game was played"
                                },
                                {
                                    "name": "round",
                                    "dataType": ["string"],
                                    "description": "Round number in the tournament"
                                },
                                {
                                    "name": "moveCount",
                                    "dataType": ["int"],
                                    "description": "Number of moves in the game"
                                },
                                {
                                    "name": "openingMoves",
                                    "dataType": ["string"],
                                    "description": "Opening moves in SAN notation (first 10-15 moves)"
                                },
                                {
                                    "name": "whiteElo",
                                    "dataType": ["int"],
                                    "description": "ELO rating of white player"
                                },
                                {
                                    "name": "blackElo",
                                    "dataType": ["int"],
                                    "description": "ELO rating of black player"
                                },
                                {
                                    "name": "source",
                                    "dataType": ["string"],
                                    "description": "Source of the game data (e.g., 'TWIC', 'Lichess')"
                                },
                                {
                                    "name": "importDate",
                                    "dataType": ["date"],
                                    "description": "Date when game was imported into the system"
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
    
    def _parse_pgn_to_object(self, pgn_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse PGN text into a structured object for storage.
        
        Args:
            pgn_text: PGN text to parse
            
        Returns:
            Dictionary with game data or None if parsing failed
        """
        try:
            # Parse the PGN text
            pgn_io = io.StringIO(pgn_text)
            game = chess.pgn.read_game(pgn_io)
            
            if not game:
                return None
            
            # Extract headers
            headers = game.headers
            
            # Count moves
            move_count = 0
            node = game
            opening_moves = []
            
            # Get first 10-15 moves for opening sequence
            while not node.is_end() and move_count < 15:
                next_node = node.variations[0] if node.variations else None
                if not next_node:
                    break
                
                # Add the move in SAN notation
                opening_moves.append(node.board().san(next_node.move))
                node = next_node
                move_count += 1
            
            # Continue counting remaining moves
            while not node.is_end():
                node = node.variations[0] if node.variations else None
                if not node:
                    break
                move_count += 1
            
            # Create game object
            game_object = {
                "pgn": pgn_text,
                "white": headers.get("White", "Unknown"),
                "black": headers.get("Black", "Unknown"),
                "date": headers.get("Date", "????-??-??").replace("?", "0"),  # Handle '?' in dates
                "result": headers.get("Result", "*"),
                "eco": headers.get("ECO", ""),
                "event": headers.get("Event", ""),
                "site": headers.get("Site", ""),
                "round": headers.get("Round", ""),
                "moveCount": move_count,
                "openingMoves": " ".join(opening_moves),
                "whiteElo": int(headers.get("WhiteElo", "0") or "0"),
                "blackElo": int(headers.get("BlackElo", "0") or "0"),
                "source": "Manual Import",  # Default source
                "importDate": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            
            return game_object
        except Exception as e:
            self.logger.error(f"Error parsing PGN: {e}")
            return None
    
    def store_game(self, pgn_text: str, source: str = "Manual Import") -> Optional[str]:
        """
        Store a single game from PGN text.
        
        Args:
            pgn_text: PGN text of the game
            source: Source of the game data
            
        Returns:
            ID of the stored game or None if failed
        """
        try:
            # Parse PGN text
            game_data = self._parse_pgn_to_object(pgn_text)
            
            if not game_data:
                self.logger.warning("Failed to parse PGN text")
                return None
            
            # Set source
            game_data["source"] = source
            
            # Store in vector db
            with self.vector_store.client.batch as batch:
                uuid = batch.add_data_object(
                    data_object=game_data,
                    class_name=self.collection_name
                )
                
            self.logger.info(f"Stored game: {game_data['white']} vs {game_data['black']} ({game_data['date']})")
            return uuid
        except Exception as e:
            self.logger.error(f"Error storing game: {e}")
            return None
    
    def store_multiple_games(self, pgn_file_path: str, source: str = "Batch Import", 
                          batch_size: int = 50) -> Tuple[int, int]:
        """
        Store multiple games from a PGN file.
        
        Args:
            pgn_file_path: Path to PGN file
            source: Source of the games
            batch_size: Number of games to process in each batch
            
        Returns:
            Tuple of (number of games processed, number of games successfully stored)
        """
        try:
            if not os.path.exists(pgn_file_path):
                self.logger.error(f"PGN file not found: {pgn_file_path}")
                return 0, 0
            
            # Open PGN file
            pgn_file = open(pgn_file_path, encoding="utf-8-sig")
            
            # Process games in batches
            processed_count = 0
            success_count = 0
            batch_objects = []
            
            while True:
                # Read next game
                game = chess.pgn.read_game(pgn_file)
                
                # Check if end of file
                if game is None:
                    break
                
                processed_count += 1
                
                # Convert to string
                pgn_string = str(game)
                
                # Parse game
                game_data = self._parse_pgn_to_object(pgn_string)
                
                if game_data:
                    # Set source and add to batch
                    game_data["source"] = source
                    batch_objects.append(game_data)
                    success_count += 1
                    
                    # If batch size reached, store batch
                    if len(batch_objects) >= batch_size:
                        self._store_batch(batch_objects)
                        self.logger.info(f"Stored batch of {len(batch_objects)} games")
                        batch_objects = []
                
                # Log progress
                if processed_count % 100 == 0:
                    self.logger.info(f"Processed {processed_count} games so far...")
            
            # Store any remaining games
            if batch_objects:
                self._store_batch(batch_objects)
                self.logger.info(f"Stored final batch of {len(batch_objects)} games")
            
            # Close file
            pgn_file.close()
            
            self.logger.info(f"Completed import: {success_count}/{processed_count} games successfully stored")
            return processed_count, success_count
            
        except Exception as e:
            self.logger.error(f"Error storing multiple games: {e}")
            return processed_count if 'processed_count' in locals() else 0, success_count if 'success_count' in locals() else 0
    
    def _store_batch(self, games: List[Dict[str, Any]]) -> None:
        """
        Store a batch of games in the vector store.
        
        Args:
            games: List of game data objects
        """
        try:
            with self.vector_store.client.batch as batch:
                for game in games:
                    batch.add_data_object(
                        data_object=game,
                        class_name=self.collection_name
                    )
        except Exception as e:
            self.logger.error(f"Error storing batch: {e}")
    
    def search_games(self, query: str, limit: int = 10, 
                  filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for games using semantic search and optional filters.
        
        Args:
            query: Search query (e.g., "Sicilian Defense", "Magnus Carlsen wins")
            limit: Maximum number of results to return
            filters: Optional filter criteria (e.g., {"white": "Carlsen", "result": "1-0"})
            
        Returns:
            List of matching game data objects
        """
        try:
            # Build query
            results = self.vector_store.query(
                query_text=query,
                class_name=self.collection_name,
                limit=limit,
                filter_terms=filters
            )
            
            self.logger.info(f"Search for '{query}' returned {len(results)} results")
            return results
        except Exception as e:
            self.logger.error(f"Error searching games: {e}")
            return []
    
    def get_game_by_id(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a game by its ID.
        
        Args:
            game_id: ID of the game
            
        Returns:
            Game data object or None if not found
        """
        try:
            result = self.vector_store.client.data_object.get_by_id(
                uuid=game_id,
                class_name=self.collection_name
            )
            
            if not result:
                return None
                
            return result
        except Exception as e:
            self.logger.error(f"Error getting game by ID: {e}")
            return None
    
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
                properties=["white", "black"]
            ).with_limit(1).do()
            
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    repo = GameRepository()
    
    if repo.healthcheck():
        print("GameRepository is healthy!")
        
        # Example: Store a game
        sample_pgn = """
        [Event "Wch U20"]
        [Site "Kiljava"]
        [Date "1984.08.14"]
        [Round "7"]
        [White "Kasparov, Garry"]
        [Black "Wolff, Patrick G"]
        [Result "1-0"]
        [ECO "D55"]
        [WhiteElo "2715"]
        [BlackElo "2225"]
        
        1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3 Be7 5. Bg5 O-O 6. e3 h6
        7. Bxf6 Bxf6 8. Qc2 c5 9. dxc5 Qa5 10. cxd5 exd5 11. O-O-O Be6
        12. Kb1 Nc6 13. Bd3 Rac8 14. Nd4 Nxd4 15. exd4 Qc7 16. h4 Be7
        17. g4 Bf6 18. g5 hxg5 19. hxg5 Be7 20. Ne2 Qc6 21. f4 Bf5
        22. Bxf5 Qf3 23. Rdg1 Rc7 24. Rh3 Qb3 25. axb3 1-0
        """
        
        game_id = repo.store_game(sample_pgn, "Example")
        if game_id:
            print(f"Stored example game with ID: {game_id}")
            
            # Example: Search games
            results = repo.search_games("Kasparov")
            if results:
                print(f"Found {len(results)} games, top match: {results[0]['white']} vs {results[0]['black']}")
            else:
                print("No games found in search")
    else:
        print("GameRepository health check failed!") 