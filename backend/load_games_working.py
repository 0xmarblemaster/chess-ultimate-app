#!/usr/bin/env python3

import os
import weaviate
import chess
import chess.pgn
import datetime
import time
from typing import Dict, Any, Optional

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
            skip_init_checks=True
        )
        print("✅ Connected to Weaviate successfully")
        return client
    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {e}")
        return None

def parse_pgn_game_comprehensive(game: chess.pgn.Game, source_file_name: str, game_index: int) -> Optional[Dict[str, Any]]:
    """Parse a chess.pgn.Game object into a comprehensive dictionary."""
    headers = game.headers
    
    # Core PGN fields
    white_player = headers.get("White", "Unknown Player")
    black_player = headers.get("Black", "Unknown Player")
    event = headers.get("Event", "Unknown Event")
    site = headers.get("Site", "?")
    round_num = headers.get("Round", "?")
    result = headers.get("Result", "*")
    date_str = headers.get("Date", "????.??.??")
    event_date_str = headers.get("EventDate", "????.??.??")
    
    # Player information
    white_title = headers.get("WhiteTitle", "")
    black_title = headers.get("BlackTitle", "")
    white_fide_id = headers.get("WhiteFideId", "")
    black_fide_id = headers.get("BlackFideId", "")
    
    # Team information
    white_team = headers.get("WhiteTeam", "")
    black_team = headers.get("BlackTeam", "")
    event_type = headers.get("EventType", "")
    
    # Chess-specific information
    eco = headers.get("ECO", "")
    opening = headers.get("Opening", "")
    variation = headers.get("Variation", "")
    
    # Extract ELO ratings
    white_elo = None
    black_elo = None
    try:
        white_elo_str = headers.get("WhiteElo", "")
        if white_elo_str and white_elo_str != "?":
            white_elo = int(white_elo_str)
    except (ValueError, TypeError):
        pass
        
    try:
        black_elo_str = headers.get("BlackElo", "")
        if black_elo_str and black_elo_str != "?":
            black_elo = int(black_elo_str)
    except (ValueError, TypeError):
        pass
    
    # Parse dates
    date_utc = None
    event_date_utc = None
    
    try:
        if date_str and date_str != "????.??.??":
            for fmt in ["%Y.%m.%d", "%Y.%m", "%Y"]:
                try:
                    date_utc = datetime.datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
    except:
        pass
        
    try:
        if event_date_str and event_date_str != "????.??.??":
            for fmt in ["%Y.%m.%d", "%Y.%m", "%Y"]:
                try:
                    event_date_utc = datetime.datetime.strptime(event_date_str, fmt)
                    break
                except ValueError:
                    continue
    except:
        pass
    
    # Extract moves and positions
    san_moves_list = []
    uci_moves_list = []
    fen_at_each_ply = []
    
    board = game.board()
    for move in game.mainline_moves():
        san_moves_list.append(board.san(move))
        uci_moves_list.append(move.uci())
        board.push(move)
        fen_at_each_ply.append(board.fen())
    
    # Game analysis
    ply_count = len(san_moves_list)
    final_fen = board.fen() if fen_at_each_ply else "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    # Mid-game FEN (around move 10-15)
    mid_game_fen = final_fen
    if len(fen_at_each_ply) > 20:
        mid_game_fen = fen_at_each_ply[min(20, len(fen_at_each_ply) - 1)]
    
    # PGN moves text
    pgn_moves = " ".join(f"{i//2 + 1}.{' ' if i % 2 == 0 else '.. '}{move}" 
                        for i, move in enumerate(san_moves_list))
    
    # Computed analysis fields
    game_length_category = "short" if ply_count < 30 else "medium" if ply_count < 60 else "long"
    
    player_strength_category = "unknown"
    if white_elo and black_elo:
        avg_elo = (white_elo + black_elo) / 2
        if avg_elo >= 2400:
            player_strength_category = "master"
        elif avg_elo >= 2200:
            player_strength_category = "expert"
        elif avg_elo >= 2000:
            player_strength_category = "class_a"
        elif avg_elo >= 1800:
            player_strength_category = "class_b"
        else:
            player_strength_category = "amateur"
    
    # Opening family from ECO
    opening_family = "unknown"
    if eco:
        if eco.startswith("A"):
            opening_family = "Flank Openings"
        elif eco.startswith("B"):
            opening_family = "Semi-Open Games"
        elif eco.startswith("C"):
            opening_family = "Open Games"
        elif eco.startswith("D"):
            opening_family = "Closed Games"
        elif eco.startswith("E"):
            opening_family = "Indian Defenses"
    
    # Searchable text
    searchable_text = f"{white_player} {black_player} {event} {site} {opening} {variation}".strip()
    
    # Tags based on game characteristics
    tags = []
    if ply_count < 20:
        tags.append("short_game")
    elif ply_count > 80:
        tags.append("long_game")
    
    if result == "1-0":
        tags.append("white_wins")
    elif result == "0-1":
        tags.append("black_wins")
    elif result == "1/2-1/2":
        tags.append("draw")
    
    if white_elo and white_elo >= 2400:
        tags.append("master_level")
    if event_type == "team":
        tags.append("team_event")
    
    # Current timestamp
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Build the complete data object
    game_data = {
        # Core PGN fields
        "event": event,
        "site": site,
        "date": date_str,
        "date_utc": date_utc.isoformat() + "Z" if date_utc else None,
        "round": round_num,
        "white_player": white_player,
        "black_player": black_player,
        "result": result,
        "event_date": event_date_str,
        "event_date_utc": event_date_utc.isoformat() + "Z" if event_date_utc else None,
        
        # Player information
        "white_title": white_title if white_title else None,
        "black_title": black_title if black_title else None,
        "white_elo": white_elo,
        "black_elo": black_elo,
        "white_fide_id": white_fide_id if white_fide_id else None,
        "black_fide_id": black_fide_id if black_fide_id else None,
        
        # Team information
        "white_team": white_team if white_team else None,
        "black_team": black_team if black_team else None,
        "event_type": event_type if event_type else None,
        
        # Chess-specific information
        "eco": eco if eco else None,
        "opening": opening if opening else None,
        "variation": variation if variation else None,
        "ply_count": ply_count,
        
        # Position data
        "final_fen": final_fen,
        "mid_game_fen": mid_game_fen,
        "all_ply_fens": fen_at_each_ply,
        
        # Move data
        "pgn_moves": pgn_moves,
        "moves_san": san_moves_list,
        "moves_uci": uci_moves_list,
        
        # Computed analysis fields
        "game_length_category": game_length_category,
        "player_strength_category": player_strength_category,
        "opening_family": opening_family,
        
        # System fields
        "type": "chess_game",
        "source_file": source_file_name,
        "game_index": game_index,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        
        # Search helper fields
        "searchable_text": searchable_text,
        "tags": tags,
    }
    
    # Filter out None values
    return {k: v for k, v in game_data.items() if v is not None}

def load_games_working():
    """Load games using individual inserts (proven to work)."""
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
        total_errors = 0
        
        with open(pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                try:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    total_games += 1
                    
                    # Parse game
                    game_data = parse_pgn_game_comprehensive(game, "twic1590.pgn", total_games - 1)
                    
                    if game_data:
                        # Create deterministic UUID
                        uuid_string = f"{game_data['white_player']}_{game_data['black_player']}_{game_data.get('date', '')}_{game_data['event']}_{total_games}"
                        uuid = weaviate.util.generate_uuid5(uuid_string)
                        
                        try:
                            # Insert individual game (proven to work)
                            result = collection.data.insert(
                                properties=game_data,
                                uuid=uuid
                            )
                            total_imported += 1
                            
                            if total_imported % 50 == 0:
                                print(f"  ✅ Imported {total_imported}/{total_games} games...")
                                
                        except Exception as e:
                            print(f"  ❌ Error inserting game {total_games}: {e}")
                            total_errors += 1
                    
                    if total_games % 500 == 0:
                        print(f"  📊 Processed {total_games} games...")
                        
                except Exception as e:
                    print(f"  ⚠️ Error parsing game {total_games}: {e}")
                    total_errors += 1
                    continue
        
        print(f"\n🎉 Loading Complete!")
        print(f"📊 Summary:")
        print(f"   - Total games processed: {total_games}")
        print(f"   - Successfully imported: {total_imported}")
        print(f"   - Errors: {total_errors}")
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
    print("🚀 Starting Working Games Loader")
    print("=" * 50)
    load_games_working()
    print("✅ Working games loader finished") 