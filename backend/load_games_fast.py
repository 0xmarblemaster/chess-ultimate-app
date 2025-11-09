#!/usr/bin/env python3

import os
import weaviate
import chess
import chess.pgn
import datetime
import time
from typing import Dict, Any, Optional, List

def get_weaviate_client():
    """Get a Weaviate client that works with our setup."""
    OPENAI_API_KEY = "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"
    
    headers = {}
    if OPENAI_API_KEY:
        headers["X-OpenAI-Api-Key"] = OPENAI_API_KEY
    
    try:
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True  # Skip gRPC health checks
        )
        print("✅ Connected to Weaviate successfully")
        return client
    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {e}")
        return None

def parse_pgn_game_fast(game: chess.pgn.Game, source_file_name: str, game_index: int) -> Optional[Dict[str, Any]]:
    """Fast parsing of PGN game with essential fields."""
    headers = game.headers
    
    # Core fields
    white_player = headers.get("White", "Unknown")
    black_player = headers.get("Black", "Unknown")
    event = headers.get("Event", "Unknown")
    site = headers.get("Site", "?")
    result = headers.get("Result", "*")
    eco = headers.get("ECO", "")
    opening = headers.get("Opening", "")
    
    # ELO ratings
    white_elo = None
    black_elo = None
    try:
        white_elo_str = headers.get("WhiteElo", "")
        if white_elo_str and white_elo_str != "?":
            white_elo = int(white_elo_str)
    except:
        pass
        
    try:
        black_elo_str = headers.get("BlackElo", "")
        if black_elo_str and black_elo_str != "?":
            black_elo = int(black_elo_str)
    except:
        pass
    
    # Extract moves quickly
    san_moves = []
    board = game.board()
    for move in game.mainline_moves():
        san_moves.append(board.san(move))
        board.push(move)
    
    ply_count = len(san_moves)
    final_fen = board.fen()
    pgn_moves = " ".join(san_moves)
    
    # Current timestamp
    now = datetime.datetime.now(datetime.timezone.utc)
    
    return {
        "white_player": white_player,
        "black_player": black_player,
        "event": event,
        "site": site,
        "result": result,
        "eco": eco if eco else None,
        "opening": opening if opening else None,
        "white_elo": white_elo,
        "black_elo": black_elo,
        "ply_count": ply_count,
        "final_fen": final_fen,
        "pgn_moves": pgn_moves,
        "type": "chess_game",
        "source_file": source_file_name,
        "game_index": game_index,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

def load_games_fast():
    """Load games with smaller batches for faster feedback."""
    client = get_weaviate_client()
    if not client:
        return
    
    try:
        if not client.collections.exists("ChessGame"):
            print("❌ ChessGame collection does not exist.")
            return
        
        collection = client.collections.get("ChessGame")
        
        # Check current count
        try:
            current_count = collection.aggregate.over_all(total_count=True).total_count
            print(f"📊 Current games in database: {current_count}")
        except:
            print("📊 Current games in database: unknown")
        
        pgn_file = "data/twic_pgn/twic1590.pgn"
        if not os.path.exists(pgn_file):
            print(f"❌ PGN file not found: {pgn_file}")
            return
        
        print(f"📂 Processing {pgn_file}...")
        
        total_games = 0
        total_imported = 0
        batch_size = 50  # Smaller batches
        
        batch_data = []
        
        with open(pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                try:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    total_games += 1
                    
                    # Parse game
                    game_data = parse_pgn_game_fast(game, "twic1590.pgn", total_games - 1)
                    
                    if game_data:
                        # Create UUID
                        uuid_string = f"{game_data['white_player']}_{game_data['black_player']}_{game_data['event']}_{total_games}"
                        uuid = weaviate.util.generate_uuid5(uuid_string)
                        
                        batch_data.append({
                            "properties": game_data,
                            "uuid": uuid
                        })
                        
                        # Process batch when it reaches batch_size
                        if len(batch_data) >= batch_size:
                            try:
                                with collection.batch.fixed_size(batch_size) as batch:
                                    for item in batch_data:
                                        batch.add_object(
                                            properties=item["properties"],
                                            uuid=item["uuid"]
                                        )
                                
                                total_imported += len(batch_data)
                                print(f"  ✅ Imported batch: {total_imported}/{total_games} games")
                                batch_data = []
                                
                            except Exception as e:
                                print(f"  ❌ Batch import error: {e}")
                                batch_data = []
                    
                    if total_games % 500 == 0:
                        print(f"  📊 Processed {total_games} games...")
                        
                except Exception as e:
                    print(f"  ⚠️ Error parsing game {total_games}: {e}")
                    continue
        
        # Process remaining batch
        if batch_data:
            try:
                with collection.batch.fixed_size(len(batch_data)) as batch:
                    for item in batch_data:
                        batch.add_object(
                            properties=item["properties"],
                            uuid=item["uuid"]
                        )
                
                total_imported += len(batch_data)
                print(f"  ✅ Imported final batch: {total_imported}/{total_games} games")
                
            except Exception as e:
                print(f"  ❌ Final batch import error: {e}")
        
        print(f"\n🎉 Loading Complete!")
        print(f"📊 Summary:")
        print(f"   - Total games processed: {total_games}")
        print(f"   - Successfully imported: {total_imported}")
        print(f"   - Success rate: {(total_imported/total_games*100):.1f}%" if total_games > 0 else "   - Success rate: 0%")
        
        # Final count check
        try:
            final_count = collection.aggregate.over_all(total_count=True).total_count
            print(f"   - Final database count: {final_count}")
        except:
            print("   - Final database count: unknown")
        
    except Exception as e:
        print(f"❌ Error during loading: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            # client.close() removed - Weaviate client manages connections automatically
            print("🔌 Weaviate connection closed")
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Fast Games Loader")
    print("=" * 50)
    load_games_fast()
    print("✅ Fast games loader finished") 