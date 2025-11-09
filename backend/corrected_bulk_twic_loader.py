#!/usr/bin/env python3
"""
Corrected TWIC Bulk Loader - Systematic Database Upload
======================================================

Loads all 673 TWIC files into Weaviate database one by one with:
- Progress tracking and resume capability 
- Fixed ELO handling (strings to floats)
- Detailed logging and statistics
- Error handling with fallback
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
        logging.FileHandler('corrected_bulk_twic_loader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CorrectedTWICBulkLoader:
    def __init__(self):
        self.twic_dir = Path("data/twic_pgn/twic_downloads/all_extracted_pgn")
        self.progress_file = Path("corrected_loader_progress.json")
        self.stats_file = Path("corrected_loader_stats.json")
        
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
            "total_stats": {
                "files_processed": 0,
                "total_games_loaded": 0,
                "total_games_failed": 0,
                "start_time": None
            }
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
            "session_start": time.time(),
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
    
    def safe_elo_convert(self, elo_str: str) -> Optional[float]:
        """Safely convert ELO string to float, handling empty values."""
        if not elo_str or str(elo_str).strip() == "" or str(elo_str).strip() == "?":
            return None
        try:
            # Handle case where it might already be a number
            if isinstance(elo_str, (int, float)):
                return float(elo_str)
            # Convert string to float
            cleaned = str(elo_str).strip()
            if cleaned == "":
                return None
            return float(cleaned)
        except (ValueError, TypeError) as e:
            logger.debug(f"Could not convert ELO '{elo_str}' to float: {e}")
            return None
    
    def parse_game(self, game: chess.pgn.Game, source_file: str, game_index: int) -> Optional[Dict[str, Any]]:
        """Parse a chess game into Weaviate format with safe ELO handling."""
        try:
            headers = game.headers
            
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
            
            # Handle ELO ratings safely - ONLY add if conversion succeeds
            white_elo_raw = headers.get("WhiteElo", "")
            black_elo_raw = headers.get("BlackElo", "")
            
            white_elo = self.safe_elo_convert(white_elo_raw)
            black_elo = self.safe_elo_convert(black_elo_raw)
            
            # Only include ELO fields if they have valid values
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
    
    def insert_batch(self, batch: List[Dict]) -> Dict[str, int]:
        """Insert a batch of games into Weaviate with detailed error tracking."""
        success_count = 0
        failed_count = 0
        
        try:
            # Use batch insertion
            with self.collection.batch.dynamic() as batch_context:
                for i, game_data in enumerate(batch):
                    try:
                        batch_context.add_object(properties=game_data)
                        success_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to add game {i} to batch: {e}")
                        failed_count += 1
                        
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            failed_count = len(batch)
            
        return {"success": success_count, "failed": failed_count}
    
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
                batch_size = 50  # Smaller batch size for better error handling
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
                            batch_result = self.insert_batch(batch)
                            result["games_loaded"] += batch_result["success"]
                            result["games_failed"] += batch_result["failed"]
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
                    batch_result = self.insert_batch(batch)
                    result["games_loaded"] += batch_result["success"]
                    result["games_failed"] += batch_result["failed"]
        
        except Exception as e:
            error_msg = f"Failed to process file {file_name}: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        # Update timing
        result["processing_time"] = time.time() - start_time
        
        # Update progress
        self.progress["processed_files"].append(file_name)
        self.progress["total_stats"]["files_processed"] += 1
        self.progress["total_stats"]["total_games_loaded"] += result["games_loaded"]
        self.progress["total_stats"]["total_games_failed"] += result["games_failed"]
        if not self.progress["total_stats"]["start_time"]:
            self.progress["total_stats"]["start_time"] = time.time()
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
    
    def print_progress_report(self, current_file_index: int, total_files: int):
        """Print a progress report."""
        percent = (current_file_index / total_files) * 100
        
        print(f"\n" + "="*60)
        print(f"📊 CORRECTED TWIC LOADING PROGRESS REPORT")
        print(f"="*60)
        print(f"Progress: {percent:.1f}% ({current_file_index}/{total_files} files)")
        print(f"Files processed: {self.progress['total_stats']['files_processed']}")
        print(f"Total games loaded: {self.progress['total_stats']['total_games_loaded']:,}")
        print(f"Failed games: {self.progress['total_stats']['total_games_failed']:,}")
        
        if self.progress["total_stats"]["start_time"]:
            session_time = time.time() - self.progress["total_stats"]["start_time"]
            print(f"Session time: {session_time/60:.1f} minutes")
            
            if current_file_index > 0:
                avg_time_per_file = session_time / current_file_index
                remaining_files = total_files - current_file_index
                eta_seconds = remaining_files * avg_time_per_file
                print(f"ETA: {eta_seconds/3600:.1f} hours")
        
        print(f"="*60)
    
    def check_stop_signal(self) -> bool:
        """Check if stop signal file exists."""
        stop_file = Path("stop_signal.txt")
        return stop_file.exists()
    
    def run(self):
        """Main loading process."""
        logger.info("🚀 Starting Corrected TWIC Bulk Loading Process")
        
        # Connect to Weaviate
        if not self.connect_to_weaviate():
            logger.error("Cannot connect to Weaviate. Exiting.")
            return False
        
        # Get all TWIC files
        twic_files = self.get_twic_files()
        logger.info(f"Found {len(twic_files)} TWIC files to process")
        
        # Filter out already processed files
        processed_files = set(self.progress["processed_files"])
        remaining_files = [f for f in twic_files if f.name not in processed_files]
        
        logger.info(f"Resuming from {len(processed_files)} already processed files")
        logger.info(f"Remaining files to process: {len(remaining_files)}")
        
        if not remaining_files:
            logger.info("✅ All files already processed!")
            return True
        
        # Process each file
        for i, file_path in enumerate(remaining_files):
            try:
                # Check for stop signal before processing each file
                if self.check_stop_signal():
                    logger.info("🛑 Stop signal detected. Finishing current operations and exiting gracefully.")
                    logger.info(f"📊 Final Stats: {len(processed_files) + i} files processed")
                    logger.info(f"📊 Total games loaded: {self.progress['total_stats']['total_games_loaded']:,}")
                    return True
                
                current_index = len(processed_files) + i + 1
                self.print_progress_report(current_index - 1, len(twic_files))
                
                result = self.load_twic_file(file_path)
                
                if result["games_loaded"] == 0 and result["games_processed"] > 0:
                    logger.warning(f"⚠️  No games loaded from {file_path.name} - check ELO handling")
                
                # Brief pause between files
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Critical error processing {file_path.name}: {e}")
                self.progress["failed_files"].append(file_path.name)
                self.save_progress()
                continue
        
        # Final report
        self.print_progress_report(len(twic_files), len(twic_files))
        logger.info("🎉 TWIC Bulk Loading Complete!")
        
        return True

def main():
    loader = CorrectedTWICBulkLoader()
    loader.run()

if __name__ == "__main__":
    main() 