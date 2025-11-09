#!/usr/bin/env python3
"""
2025 TWIC Loader - Load TWIC files 1574-1594 for complete 2025 coverage
======================================================================

This script focuses specifically on loading the 2025 TWIC files to ensure
we have complete coverage for the year 2025.
"""

import os
import json
import time
import weaviate
import chess
import chess.pgn
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_2025_twics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TWIC2025Loader:
    def __init__(self):
        self.twic_dir = Path("data/twic_pgn/twic_downloads/all_extracted_pgn")
        self.progress_file = Path("twic_2025_progress.json")
        
        # Target TWIC range for 2025
        self.target_range = list(range(1574, 1595))  # 1574-1594 inclusive
        
        # Weaviate setup using existing configuration
        self.client = None
        self.collection = None
        
        # Progress tracking
        self.progress = self.load_progress()
        
    def load_progress(self) -> Dict:
        """Load existing progress from file."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "processed_files": [],
            "failed_files": [],
            "current_file": None,
            "start_time": time.time(),
            "total_games_loaded": 0,
            "total_games_failed": 0
        }
    
    def save_progress(self):
        """Save current progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def connect_to_weaviate(self) -> bool:
        """Connect to Weaviate using existing configuration."""
        try:
            import sys
            sys.path.insert(0, '/home/marblemaster/Desktop/Cursor/mvp1')
            from backend.etl.weaviate_loader import get_weaviate_client
            
            self.client = get_weaviate_client()
            if not self.client:
                logger.error("❌ Failed to get Weaviate client")
                return False
                
            self.collection = self.client.collections.get("ChessGame")
            logger.info("✅ Connected to Weaviate successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Weaviate: {e}")
            return False
    
    def get_2025_twic_files(self) -> List[Path]:
        """Get TWIC files for 2025 (1574-1594) in order."""
        files = []
        
        for twic_num in self.target_range:
            file_pattern = f"twic{twic_num}_twic{twic_num}.pgn"
            file_path = self.twic_dir / file_pattern
            
            if file_path.exists():
                files.append(file_path)
                logger.info(f"✅ Found TWIC {twic_num}: {file_path.name}")
            else:
                logger.warning(f"❌ Missing TWIC {twic_num}: {file_pattern}")
        
        logger.info(f"📁 Found {len(files)} TWIC files for 2025 (target: {len(self.target_range)})")
        return files
    
    def safe_elo_convert(self, elo_str: str) -> Optional[float]:
        """Safely convert ELO string to float."""
        if not elo_str or str(elo_str).strip() == "" or str(elo_str).strip() == "?":
            return None
        try:
            if isinstance(elo_str, (int, float)):
                return float(elo_str)
            cleaned = str(elo_str).strip()
            if cleaned == "":
                return None
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def parse_game(self, game: chess.pgn.Game, source_file: str, game_index: int) -> Optional[Dict[str, Any]]:
        """Parse a chess game into Weaviate format."""
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
                
                # Extended fields
                "eco": headers.get("ECO", ""),
                "opening": headers.get("Opening", ""),
                "event_date": headers.get("EventDate", ""),
                
                # Move data
                "moves": str(game).strip(),
                "move_count": float(len(list(game.mainline_moves()))),
                
                # Generate FEN positions
                "starting_fen": game.board().fen(),
            }
            
            # Handle ELO ratings safely
            white_elo = self.safe_elo_convert(headers.get("WhiteElo", ""))
            black_elo = self.safe_elo_convert(headers.get("BlackElo", ""))
            
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
            logger.error(f"❌ Error parsing game {game_index}: {e}")
            return None
    
    def load_twic_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single TWIC file into Weaviate."""
        logger.info(f"📁 Loading {file_path.name}")
        
        stats = {
            "file": file_path.name,
            "start_time": time.time(),
            "games_processed": 0,
            "games_loaded": 0,
            "games_failed": 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                game_index = 0
                batch = []
                batch_size = 100
                
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    game_index += 1
                    stats["games_processed"] = game_index
                    
                    # Parse game
                    game_data = self.parse_game(game, file_path.name, game_index)
                    if game_data:
                        batch.append(game_data)
                    else:
                        stats["games_failed"] += 1
                    
                    # Insert batch when full
                    if len(batch) >= batch_size:
                        batch_stats = self.insert_batch(batch)
                        stats["games_loaded"] += batch_stats["success"]
                        stats["games_failed"] += batch_stats["failed"]
                        batch = []
                        
                        # Progress report every 1000 games
                        if game_index % 1000 == 0:
                            logger.info(f"   📊 {file_path.name}: {game_index} games processed, {stats['games_loaded']} loaded")
                
                # Insert remaining games
                if batch:
                    batch_stats = self.insert_batch(batch)
                    stats["games_loaded"] += batch_stats["success"]
                    stats["games_failed"] += batch_stats["failed"]
                
                stats["end_time"] = time.time()
                stats["duration"] = stats["end_time"] - stats["start_time"]
                
                logger.info(f"✅ {file_path.name} complete: {stats['games_loaded']}/{stats['games_processed']} games loaded in {stats['duration']:.1f}s")
                
        except Exception as e:
            logger.error(f"❌ Error loading {file_path.name}: {e}")
            stats["error"] = str(e)
            
        return stats
    
    def insert_batch(self, batch: List[Dict]) -> Dict[str, int]:
        """Insert a batch of games into Weaviate."""
        try:
            response = self.collection.data.insert_many(batch)
            
            # Use the current Weaviate client format: errors and uuids
            if hasattr(response, 'errors') and hasattr(response, 'uuids'):
                # Current format
                error_count = len(response.errors) if response.errors else 0
                uuid_count = len(response.uuids) if response.uuids else 0
                success_count = uuid_count
                failed_count = error_count
                
                if failed_count > 0:
                    logger.warning(f"⚠️ Batch had {failed_count} failures out of {len(batch)} games")
                    # Log first few errors for debugging
                    for i, error in enumerate(response.errors[:3]):
                        logger.warning(f"   Error {i+1}: {error}")
                
                return {"success": success_count, "failed": failed_count}
            else:
                # Fallback for unknown format
                logger.warning(f"⚠️ Unknown response format: {type(response)}, assuming all {len(batch)} succeeded")
                return {"success": len(batch), "failed": 0}
            
        except Exception as e:
            logger.error(f"❌ Batch insert error: {e}")
            return {"success": 0, "failed": len(batch)}
    
    def check_stop_signal(self) -> bool:
        """Check if stop signal file exists."""
        return Path("stop_2025_loading.txt").exists()
    
    def run(self):
        """Run the 2025 TWIC loading process."""
        logger.info("🚀 Starting 2025 TWIC Loader (files 1574-1594)")
        
        # Connect to Weaviate
        if not self.connect_to_weaviate():
            logger.error("❌ Cannot proceed without Weaviate connection")
            return
        
        # Get files to process
        twic_files = self.get_2025_twic_files()
        if not twic_files:
            logger.error("❌ No TWIC files found for 2025")
            return
        
        # Filter out already processed files
        remaining_files = [f for f in twic_files if f.name not in self.progress["processed_files"]]
        
        logger.info(f"📋 Files to process: {len(remaining_files)}/{len(twic_files)}")
        logger.info(f"📊 Already processed: {len(self.progress['processed_files'])} files")
        
        # Process files
        for i, file_path in enumerate(remaining_files):
            if self.check_stop_signal():
                logger.info("🛑 Stop signal detected, halting process")
                break
            
            logger.info(f"📁 Processing file {i+1}/{len(remaining_files)}: {file_path.name}")
            
            # Update current file
            self.progress["current_file"] = file_path.name
            self.save_progress()
            
            # Load file
            file_stats = self.load_twic_file(file_path)
            
            # Update progress
            if "error" not in file_stats:
                self.progress["processed_files"].append(file_path.name)
                self.progress["total_games_loaded"] += file_stats["games_loaded"]
                self.progress["total_games_failed"] += file_stats["games_failed"]
            else:
                self.progress["failed_files"].append(file_path.name)
            
            self.save_progress()
            
            # Progress report
            logger.info(f"📊 Overall progress: {len(self.progress['processed_files'])}/{len(twic_files)} files, {self.progress['total_games_loaded']} total games loaded")
        
        self.progress["current_file"] = None
        self.progress["end_time"] = time.time()
        self.save_progress()
        
        logger.info("🎉 2025 TWIC loading complete!")
        logger.info(f"📊 Final stats: {len(self.progress['processed_files'])}/{len(twic_files)} files processed")
        logger.info(f"🎮 Games loaded: {self.progress['total_games_loaded']}")
        logger.info(f"❌ Games failed: {self.progress['total_games_failed']}")
        
        if self.client:
            # self.client.close() removed - Weaviate client manages connections automatically

def main():
    """Main entry point."""
    loader = TWIC2025Loader()
    loader.run()

if __name__ == "__main__":
    main() 