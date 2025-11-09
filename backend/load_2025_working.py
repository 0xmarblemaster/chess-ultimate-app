#!/usr/bin/env python3
"""
Simple TWIC Loader - Robust Database Upload
==========================================

Simplified version that handles data types correctly.
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

def get_weaviate_client():
    """Get Weaviate client."""
    openai_key = "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"
    
    headers = {}
    if openai_key:
        headers["X-OpenAI-Api-Key"] = openai_key
    
    try:
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True
        )
        print("✅ Connected to Weaviate successfully")
        return client
    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {e}")
        return None

def safe_float(value: str) -> Optional[float]:
    """Safely convert string to float."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return None

def parse_game_simple(game: chess.pgn.Game, source_file: str, game_index: int) -> Optional[Dict[str, Any]]:
    """Parse a chess game with proper data types."""
    try:
        headers = game.headers
        
        # Basic required fields
        game_data = {
            "white_player": headers.get("White", "Unknown"),
            "black_player": headers.get("Black", "Unknown"), 
            "event": headers.get("Event", "Unknown"),
            "site": headers.get("Site", "?"),
            "round": headers.get("Round", "?"),
            "result": headers.get("Result", "*"),
            "date": headers.get("Date", "????.??.??"),
            "source_file": source_file,
            "moves": str(game).strip(),
        }
        
        # Optional float fields - only add if valid
        white_elo = safe_float(headers.get("WhiteElo", ""))
        black_elo = safe_float(headers.get("BlackElo", ""))
        
        if white_elo is not None:
            game_data["white_elo"] = white_elo
        if black_elo is not None:
            game_data["black_elo"] = black_elo
        
        # Optional string fields
        eco = headers.get("ECO", "")
        if eco:
            game_data["eco"] = eco
            
        opening = headers.get("Opening", "")
        if opening:
            game_data["opening"] = opening
            
        time_control = headers.get("TimeControl", "")
        if time_control:
            game_data["time_control"] = time_control
            
        event_date = headers.get("EventDate", "")
        if event_date:
            game_data["event_date"] = event_date
        
        # FEN positions
        try:
            game_data["starting_fen"] = game.board().fen()
            
            # Get ending position
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            game_data["ending_fen"] = board.fen()
            
            # Move count
            game_data["move_count"] = len(list(game.mainline_moves()))
        except Exception as e:
            print(f"Warning: Could not process moves for game {game_index}: {e}")
            game_data["starting_fen"] = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            game_data["ending_fen"] = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            game_data["move_count"] = 0
        
        return game_data
        
    except Exception as e:
        print(f"Failed to parse game {game_index} from {source_file}: {e}")
        return None

def load_single_twic_file(client, file_path: Path) -> Dict[str, Any]:
    """Load a single TWIC file."""
    file_name = file_path.name
    start_time = time.time()
    
    print(f"\n📁 Processing {file_name}...")
    
    result = {
        "file": file_name,
        "games_processed": 0,
        "games_loaded": 0,
        "games_failed": 0,
        "processing_time": 0
    }
    
    try:
        collection = client.collections.get("ChessGame")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            game_index = 0
            batch = []
            batch_size = 50  # Smaller batches
            
            while True:
                try:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    game_index += 1
                    result["games_processed"] += 1
                    
                    # Parse game
                    game_data = parse_game_simple(game, file_name, game_index)
                    if game_data:
                        batch.append(game_data)
                    else:
                        result["games_failed"] += 1
                    
                    # Process batch
                    if len(batch) >= batch_size:
                        try:
                            with collection.batch.dynamic() as batch_context:
                                for data in batch:
                                    batch_context.add_object(properties=data)
                            result["games_loaded"] += len(batch)
                            print(f"   Loaded batch: {result['games_loaded']} games")
                        except Exception as e:
                            print(f"   Batch failed: {e}")
                            result["games_failed"] += len(batch)
                        
                        batch = []
                    
                    # Progress update every 1000 games
                    if game_index % 1000 == 0:
                        print(f"   Processed {game_index} games...")
                
                except Exception as e:
                    print(f"   Error processing game {game_index}: {e}")
                    result["games_failed"] += 1
                    continue
            
            # Process remaining batch
            if batch:
                try:
                    with collection.batch.dynamic() as batch_context:
                        for data in batch:
                            batch_context.add_object(properties=data)
                    result["games_loaded"] += len(batch)
                    print(f"   Loaded final batch: {result['games_loaded']} total games")
                except Exception as e:
                    print(f"   Final batch failed: {e}")
                    result["games_failed"] += len(batch)
    
    except Exception as e:
        print(f"❌ Failed to process file {file_name}: {e}")
    
    result["processing_time"] = time.time() - start_time
    print(f"✅ {file_name}: {result['games_loaded']}/{result['games_processed']} games loaded in {result['processing_time']:.1f}s")
    
    return result

def main():
    """Main loading process for 2025 TWIC files."""
    print("🚀 Starting 2025 TWIC Loading Process (Files 1574-1594)")
    print("📅 Loading chess games from 2025")
    print("=" * 60)
    
    # Connect to Weaviate
    client = get_weaviate_client()
    if not client:
        return
    
    # Get only 2025 TWIC files (1574-1594)
    twic_dir = Path("data/twic_pgn/twic_downloads/all_extracted_pgn")
    target_files = [f"twic{i}_twic{i}.pgn" for i in range(1574, 1595)]
    
    # Filter to only existing files
    twic_files = []
    for target_file in target_files:
        file_path = twic_dir / target_file
        if file_path.exists():
            twic_files.append(file_path)
        else:
            print(f"❌ File not found: {target_file}")
    
    print(f"📁 Found {len(twic_files)} out of {len(target_files)} target 2025 TWIC files")
    
    # Check current database state
    try:
        collection = client.collections.get("ChessGame")
        total_before = collection.aggregate.over_all(total_count=True).total_count
        print(f"📊 Current database: {total_before:,} games")
    except Exception as e:
        print(f"Could not check database state: {e}")
        total_before = 0
    
    # Load progress for 2025 loading
    progress_file = Path("twic_2025_loader_progress.json")
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            processed_files = json.load(f).get("processed_files", [])
    else:
        processed_files = []
    
    # Process files
    total_stats = {
        "files_processed": 0,
        "total_games_loaded": 0,
        "total_games_failed": 0,
        "start_time": time.time()
    }
    
    for i, file_path in enumerate(twic_files, 1):
        file_name = file_path.name
        
        # Skip if already processed
        if file_name in processed_files:
            print(f"⏭️  Skipping {file_name} (already processed)")
            continue
        
        print(f"\n🎯 Processing file {i}/{len(twic_files)}: {file_name}")
        
        # Load the file
        try:
            result = load_single_twic_file(client, file_path)
            
            # Update stats
            total_stats["files_processed"] += 1
            total_stats["total_games_loaded"] += result["games_loaded"]
            total_stats["total_games_failed"] += result["games_failed"]
            
            # Save progress
            processed_files.append(file_name)
            with open(progress_file, 'w') as f:
                json.dump({
                    "processed_files": processed_files,
                    "total_stats": total_stats,
                    "current_file": file_name,
                    "last_updated": time.time()
                }, f, indent=2)
            
            # Progress report
                elapsed = time.time() - total_stats["start_time"]
            remaining = len(twic_files) - total_stats["files_processed"]
            if total_stats["files_processed"] > 0:
                avg_per_file = elapsed / total_stats["files_processed"]
                eta_minutes = remaining * avg_per_file / 60
                
                print(f"\n📊 PROGRESS UPDATE:")
                print(f"   Files: {total_stats['files_processed']}/{len(twic_files)} ({total_stats['files_processed']/len(twic_files)*100:.1f}%)")
                print(f"   Games loaded: {total_stats['total_games_loaded']:,}")
                print(f"   Time elapsed: {elapsed/60:.1f} minutes")
                print(f"   ETA: {eta_minutes:.1f} minutes")
        
        except KeyboardInterrupt:
            print("⏸️  Process interrupted by user")
            break
        except Exception as e:
            print(f"❌ Failed to process {file_name}: {e}")
            continue
    
    # Final report
    elapsed = time.time() - total_stats["start_time"]
    print(f"\n🎉 2025 TWIC LOADING COMPLETE!")
    print(f"   Files processed: {total_stats['files_processed']}")
    print(f"   Games loaded: {total_stats['total_games_loaded']:,}")
    print(f"   Failed games: {total_stats['total_games_failed']}")
    print(f"   Session time: {elapsed/60:.1f} minutes")
    
    # Check final database state
    try:
        total_after = collection.aggregate.over_all(total_count=True).total_count
        games_added = total_after - total_before
        print(f"   Database now contains: {total_after:,} games (+{games_added:,})")
    except Exception as e:
        print(f"Could not check final database state: {e}")
    
    # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    main() 