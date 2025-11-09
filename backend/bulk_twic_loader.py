#!/usr/bin/env python3
"""
TWIC Bulk Loader - Systematic Database Upload
===========================================

Loads all 673 TWIC files into Weaviate database one by one with:
- Progress tracking
- Resume capability 
- Detailed logging
- Error handling
- Statistics reporting
"""

import os
import json
import time
import weaviate
import chess
import chess.pgn
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_twic_loader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TWICBulkLoader:
    def __init__(self):
        self.twic_dir = Path("data/twic_pgn/twic_downloads/all_extracted_pgn")
        self.progress_file = Path("twic_loading_progress.json")
        self.stats_file = Path("twic_loading_stats.json")
        
        # Weaviate setup
        self.openai_key = "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"
        self.client = None
        self.collection = None
        
        # Progress tracking
        self.progress = self.load_progress()
        self.stats = self.load_stats()
        
    def load_progress(self) -> Dict:
        """Load existing progress from file."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "processed_files": [],
            "failed_files": [],
            "current_file": None,
            "total_games_loaded": 0,
            "session_start": None
        }
    
    def save_progress(self):
        """Save current progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def load_stats(self) -> Dict:
        """Load statistics from file."""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {
            "files_processed": 0,
            "total_games": 0,
            "successful_games": 0,
            "failed_games": 0,
            "processing_times": {},
            "error_summary": {}
        }
    
    def save_stats(self):
        """Save current statistics to file."""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def connect_to_weaviate(self) -> bool:
        """Connect to Weaviate database."""
        try:
            headers = {}
            if self.openai_key:
                headers["X-OpenAI-Api-Key"] = self.openai_key
            
            self.client = weaviate.connect_to_local(
                host="localhost",
                port=8080,
                headers=headers,
                skip_init_checks=True
            )
            
            # Get ChessGame collection
            self.collection = self.client.collections.get("ChessGame")
            
            logger.info("✅ Connected to Weaviate successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Weaviate: {e}")
            return False
    
    def get_twic_files(self) -> List[Path]:
        """Get all TWIC files sorted by number."""
        files = list(self.twic_dir.glob("twic*.pgn"))
        
        # Sort by TWIC number
        def extract_twic_number(path):
            name = path.name
            if "twic" in name:
                # Extract number from twic0920_twic920.pgn or twic1590_twic1590.pgn
                parts = name.split("_")
                if len(parts) >= 2:
                    twic_part = parts[0]
                    number_str = twic_part.replace("twic", "").lstrip("0")
                    return int(number_str) if number_str else 0
            return 0
        
        files.sort(key=extract_twic_number)
        return files
    
    def parse_game(self, game: chess.pgn.Game, source_file: str, game_index: int) -> Optional[Dict[str, Any]]:
        """Parse a chess game into Weaviate format."""
        try:
            headers = game.headers
            
            # Helper function to safely convert ELO ratings
            def safe_elo_convert(elo_str: str) -> Optional[float]:
                if not elo_str or elo_str.strip() == "":
                    return None
                try:
                    return float(elo_str.strip())
                except (ValueError, TypeError):
                    return None
            
            # Basic game info
            game_data = {
                "white_player": headers.get("White", "Unknown"),
                "black_player": headers.get("Black", "Unknown"), 
                "event": headers.get("Event", "Unknown"),
                "site": headers.get("Site", "?"),
                "round": headers.get("Round", "?"),
                "result": headers.get("Result", "*"),
                "date": headers.get("Date", "????.??.??"),
                "source_file": source_file,
                "game_index": game_index,
                
                # Extended fields
                "eco": headers.get("ECO", ""),
                "opening": headers.get("Opening", ""),
                "time_control": headers.get("TimeControl", ""),
                "event_date": headers.get("EventDate", ""),
                
                # Move data
                "moves": str(game).strip(),
                "move_count": len(list(game.mainline_moves())),
                
                # Generate FEN positions
                "starting_fen": game.board().fen(),
            }
            
            # Handle ELO ratings safely
            white_elo = safe_elo_convert(headers.get("WhiteElo", ""))
            black_elo = safe_elo_convert(headers.get("BlackElo", ""))
            
            if white_elo is not None:
                game_data["white_elo"] = white_elo
            if black_elo is not None:
                game_data["black_elo"] = black_elo
            
            # Get ending position
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            game_data["ending_fen"] = board.fen()
            
            return game_data
            
        except Exception as e:
            logger.warning(f"Failed to parse game {game_index} from {source_file}: {e}")
            return None
    
    def load_twic_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single TWIC file into Weaviate."""
        file_name = file_path.name
        start_time = time.time()
        
        logger.info(f"📁 Processing {file_name}...")
        
        # Update progress
        self.progress["current_file"] = file_name
        self.save_progress()
        
        result = {
            "file": file_name,
            "games_processed": 0,
            "games_loaded": 0,
            "games_failed": 0,
            "errors": [],
            "processing_time": 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                game_index = 0
                batch_size = 100
                batch = []
                
                while True:
                    try:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        
                        game_index += 1
                        result["games_processed"] += 1
                        
                        # Parse game
                        game_data = self.parse_game(game, file_name, game_index)
                        if game_data:
                            batch.append(game_data)
                        else:
                            result["games_failed"] += 1
                        
                        # Process batch
                        if len(batch) >= batch_size:
                            loaded = self.insert_batch(batch)
                            result["games_loaded"] += loaded
                            result["games_failed"] += (len(batch) - loaded)
                            batch = []
                        
                        # Progress update every 1000 games
                        if game_index % 1000 == 0:
                            logger.info(f"   Processed {game_index} games from {file_name}")
                    
                    except Exception as e:
                        result["errors"].append(f"Game {game_index}: {str(e)}")
                        result["games_failed"] += 1
                        continue
                
                # Process remaining batch
                if batch:
                    loaded = self.insert_batch(batch)
                    result["games_loaded"] += loaded
                    result["games_failed"] += (len(batch) - loaded)
        
        except Exception as e:
            error_msg = f"Failed to process file {file_name}: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        # Update timing
        result["processing_time"] = time.time() - start_time
        
        # Update progress
        self.progress["processed_files"].append(file_name)
        self.progress["total_games_loaded"] += result["games_loaded"]
        self.save_progress()
        
        # Update stats
        self.stats["files_processed"] += 1
        self.stats["total_games"] += result["games_processed"]
        self.stats["successful_games"] += result["games_loaded"]
        self.stats["failed_games"] += result["games_failed"]
        self.stats["processing_times"][file_name] = result["processing_time"]
        if result["errors"]:
            self.stats["error_summary"][file_name] = result["errors"]
        self.save_stats()
        
        logger.info(f"✅ {file_name}: {result['games_loaded']}/{result['games_processed']} games loaded in {result['processing_time']:.1f}s")
        
        return result
    
    def insert_batch(self, batch: List[Dict]) -> int:
        """Insert a batch of games into Weaviate."""
        try:
            with self.collection.batch.dynamic() as batch_context:
                for game_data in batch:
                    batch_context.add_object(properties=game_data)
            return len(batch)
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            return 0
    
    def print_progress_report(self, current_file_index: int, total_files: int):
        """Print a progress report."""
        percent = (current_file_index / total_files) * 100
        
        print(f"\n" + "="*60)
        print(f"📊 TWIC LOADING PROGRESS REPORT")
        print(f"="*60)
        print(f"Progress: {percent:.1f}% ({current_file_index}/{total_files} files)")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Total games loaded: {self.stats['successful_games']:,}")
        print(f"Failed games: {self.stats['failed_games']:,}")
        
        if self.progress["session_start"]:
            session_time = time.time() - self.progress["session_start"]
            print(f"Session time: {session_time/60:.1f} minutes")
            
            if current_file_index > 0:
                avg_time_per_file = session_time / current_file_index
                remaining_files = total_files - current_file_index
                eta_seconds = remaining_files * avg_time_per_file
                print(f"ETA: {eta_seconds/3600:.1f} hours")
        
        print(f"="*60)
    
    def run(self):
        """Main loading process."""
        logger.info("🚀 Starting TWIC Bulk Loading Process")
        
        # Connect to Weaviate
        if not self.connect_to_weaviate():
            return
        
        # Get all TWIC files
        twic_files = self.get_twic_files()
        logger.info(f"📁 Found {len(twic_files)} TWIC files to process")
        
        # Start session tracking
        if not self.progress["session_start"]:
            self.progress["session_start"] = time.time()
            self.save_progress()
        
        # Process each file
        processed_count = 0
        for i, file_path in enumerate(twic_files, 1):
            file_name = file_path.name
            
            # Skip if already processed
            if file_name in self.progress["processed_files"]:
                logger.info(f"⏭️  Skipping {file_name} (already processed)")
                processed_count += 1
                continue
            
            # Load the file
            try:
                result = self.load_twic_file(file_path)
                processed_count += 1
                
                # Print progress every 10 files
                if processed_count % 10 == 0:
                    self.print_progress_report(processed_count, len(twic_files))
                
            except KeyboardInterrupt:
                logger.info("⏸️  Process interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Failed to process {file_name}: {e}")
                self.progress["failed_files"].append(file_name)
                self.save_progress()
                continue
        
        # Final report
        logger.info("🏁 TWIC Bulk Loading Complete!")
        self.print_progress_report(processed_count, len(twic_files))
        
        # Close Weaviate connection
        if self.client:
            # self.client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    loader = TWICBulkLoader()
    loader.run() 