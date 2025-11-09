import os
import weaviate
import chess
import chess.pgn
import datetime
import time
from typing import Dict, Any, Optional, List

# Import configuration from the parent directory
try:
    from . import config as etl_config
except ImportError:
    # Fallback for direct execution
    import config as etl_config

# Weaviate v4 imports
from weaviate.collections.classes.config import Configure, Property, DataType, Tokenization
from weaviate.util import generate_uuid5 # For deterministic UUIDs

# --- Configuration ---
COLLECTION_NAME = getattr(etl_config, 'WEAVIATE_GAMES_CLASS_NAME', "ChessGame")
PGN_DIRECTORY = getattr(etl_config, 'PGN_DATA_DIR', os.path.join(etl_config.BASE_DIR, "data", "twic_pgn"))
BATCH_SIZE = 100 # Number of games to batch load

# --- Weaviate Client Setup (v4 style) ---
def get_weaviate_client() -> Optional[weaviate.WeaviateClient]:
    """Initializes and returns a Weaviate client (v4) if configuration is available."""
    if not etl_config.WEAVIATE_ENABLED:
        print("DEBUG: [GamesLoader] Weaviate is disabled in config.")
        return None
    try:
        http_protocol, http_address = etl_config.WEAVIATE_URL.split("://")
        http_host, http_port_str = http_address.split(":")
        http_port = int(http_port_str)
        http_secure = http_protocol == "https"

        grpc_host = http_host
        grpc_port = getattr(etl_config, 'WEAVIATE_GRPC_PORT', 50051)
        grpc_secure = getattr(etl_config, 'WEAVIATE_GRPC_SECURE', False)

        headers = {}
        if etl_config.OPENAI_API_KEY:
             headers["X-OpenAI-Api-Key"] = etl_config.OPENAI_API_KEY
             print("DEBUG: [GamesLoader] OpenAI API Key will be sent in headers to Weaviate.")
        
        # Using connect_to_custom for more control with v4
        client = weaviate.connect_to_custom(
            http_host=http_host,
            http_port=http_port,
            http_secure=http_secure,
            grpc_host=grpc_host,
            grpc_port=grpc_port,
            grpc_secure=grpc_secure,
            headers=headers,
        )
        client.connect()

        if not client.is_ready():
            print(f"ERROR: [GamesLoader] Weaviate client connected but not ready/live at {etl_config.WEAVIATE_URL}.")
            # client.close() removed - Weaviate client manages connections automatically
            return None
        print(f"DEBUG: [GamesLoader] Weaviate client (v4) initialized and ready for {etl_config.WEAVIATE_URL}.")
        return client
    except Exception as e:
        print(f"ERROR: [GamesLoader] Failed to connect to Weaviate (v4 style): {e}")
        return None

# --- Schema Definition (v4 style) ---
def create_chess_game_collection_if_not_exists(client: weaviate.WeaviateClient):
    """Creates the ChessGame collection in Weaviate v4 if it doesn't exist."""
    if client.collections.exists(COLLECTION_NAME):
        print(f"DEBUG: [GamesLoader] Collection '{COLLECTION_NAME}' already exists.")
        return

    print(f"DEBUG: [GamesLoader] Collection '{COLLECTION_NAME}' does not exist. Creating...")
    try:
        client.collections.create(
            name=COLLECTION_NAME,
            description="A collection of chess games with metadata and moves, sourced from PGN files (e.g., TWIC).",
            vectorizer_config=Configure.Vectorizer.text2vec_openai( # Default vectorizer, can be none if not needed for all fields
                model="text-embedding-3-small", 
                vectorize_collection_name=False
            ),
            properties=[
                Property(name="white_player", data_type=DataType.TEXT, description="Name of the white player.", tokenization=Tokenization.WORD),
                Property(name="black_player", data_type=DataType.TEXT, description="Name of the black player.", tokenization=Tokenization.WORD),
                Property(name="white_elo", data_type=DataType.NUMBER, description="ELO rating of the white player."),
                Property(name="black_elo", data_type=DataType.NUMBER, description="ELO rating of the black player."),
                Property(name="white_title", data_type=DataType.TEXT, description="Title of the white player (GM, IM, FM, etc.).", tokenization=Tokenization.FIELD),
                Property(name="black_title", data_type=DataType.TEXT, description="Title of the black player (GM, IM, FM, etc.).", tokenization=Tokenization.FIELD),
                Property(name="white_fide_id", data_type=DataType.TEXT, description="FIDE ID of the white player.", tokenization=Tokenization.FIELD),
                Property(name="black_fide_id", data_type=DataType.TEXT, description="FIDE ID of the black player.", tokenization=Tokenization.FIELD),
                Property(name="event", data_type=DataType.TEXT, description="Name of the tournament or event.", tokenization=Tokenization.WORD),
                Property(name="site", data_type=DataType.TEXT, description="Location of the event.", tokenization=Tokenization.WORD),
                Property(name="round", data_type=DataType.TEXT, description="Round number or identifier.", tokenization=Tokenization.FIELD),
                Property(name="date_utc", data_type=DataType.DATE, description="Date of the game (UTC)."),
                Property(name="event_date", data_type=DataType.DATE, description="Start date of the event (UTC)."),
                Property(name="result", data_type=DataType.TEXT, description="Result of the game (e.g., 1-0, 0-1, 1/2-1/2).", tokenization=Tokenization.FIELD),
                Property(name="eco", data_type=DataType.TEXT, description="ECO (Encyclopedia of Chess Openings) code.", tokenization=Tokenization.FIELD),
                Property(name="opening_name", data_type=DataType.TEXT, description="Name of the opening played.", tokenization=Tokenization.WORD), # Added for easier search
                Property(name="ply_count", data_type=DataType.NUMBER, description="Total number of plies (half-moves) in the game."),
                Property(name="final_fen", data_type=DataType.TEXT, description="FEN of the final position.", tokenization=Tokenization.WHITESPACE),
                Property(name="mid_game_fen", data_type=DataType.TEXT, description="FEN around move 10-15 for position-based search.", tokenization=Tokenization.WHITESPACE), # For positional search
                Property(name="pgn_moves", data_type=DataType.TEXT, description="Full PGN move text.", tokenization=Tokenization.WHITESPACE), # Store full PGN for reference
                Property(name="type", data_type=DataType.TEXT, description="Object type, e.g., 'chess_game'.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="source_file", data_type=DataType.TEXT, description="Name of the PGN file from which this game was extracted.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="all_ply_fens", data_type=DataType.TEXT_ARRAY, description="An ordered list of FEN strings, one for each ply (half-move) of the game, from ply 1 to the end.", tokenization=Tokenization.FIELD, skip_vectorization=True), # New Property
            ],
            inverted_index_config=Configure.inverted_index(
                bm25_k1=1.2,
                bm25_b=0.75,
            )
        )
        print(f"DEBUG: [GamesLoader] Collection '{COLLECTION_NAME}' created successfully.")
    except Exception as e:
        print(f"ERROR: [GamesLoader] Failed to create collection '{COLLECTION_NAME}': {e}")
        raise

# --- Game Parser and Loader ---
def parse_pgn_game(game: chess.pgn.Game, source_file_name: str) -> Optional[Dict[str, Any]]:
    """Parses a chess.pgn.Game object into a dictionary for Weaviate."""
    headers = game.headers
    
    white = headers.get("White", "Unknown Player")
    black = headers.get("Black", "Unknown Player")
    event = headers.get("Event", "Unknown Event")
    site = headers.get("Site", "?")
    round_num = headers.get("Round", "?")
    result = headers.get("Result", "*")
    eco = headers.get("ECO", "")
    opening_name_header = headers.get("Opening", "") # Lichess sometimes provides this
    
    # Extract ELO ratings
    white_elo_str = headers.get("WhiteElo", "")
    black_elo_str = headers.get("BlackElo", "")
    white_elo = None
    black_elo = None
    
    try:
        if white_elo_str and white_elo_str != "?":
            white_elo = int(white_elo_str)
    except (ValueError, TypeError):
        white_elo = None
        
    try:
        if black_elo_str and black_elo_str != "?":
            black_elo = int(black_elo_str)
    except (ValueError, TypeError):
        black_elo = None
    
    # Extract titles and FIDE IDs
    white_title = headers.get("WhiteTitle", "")
    black_title = headers.get("BlackTitle", "")
    white_fide_id = headers.get("WhiteFideId", "")
    black_fide_id = headers.get("BlackFideId", "")

    date_str = headers.get("Date", "????.??.??")
    event_date_str = headers.get("EventDate", "????.??.??")
    
    try:
        # Try to parse YYYY.MM.DD
        parsed_date = datetime.datetime.strptime(date_str, "%Y.%m.%d")
    except ValueError:
        try:
            # Try to parse YYYY.MM (assuming first day of month)
            parsed_date = datetime.datetime.strptime(date_str, "%Y.%m")
        except ValueError:
            try:
                # Try to parse YYYY (assuming Jan 1st)
                parsed_date = datetime.datetime.strptime(date_str, "%Y")
            except ValueError:
                parsed_date = None # Fallback for truly unparseable dates
                
    try:
        # Try to parse event date
        parsed_event_date = datetime.datetime.strptime(event_date_str, "%Y.%m.%d")
    except ValueError:
        try:
            # Try to parse YYYY.MM (assuming first day of month)
            parsed_event_date = datetime.datetime.strptime(event_date_str, "%Y.%m")
        except ValueError:
            try:
                # Try to parse YYYY (assuming Jan 1st)
                parsed_event_date = datetime.datetime.strptime(event_date_str, "%Y")
            except ValueError:
                parsed_event_date = None # Fallback for truly unparseable dates

    # Extract moves as SAN
    san_moves_list = []
    board_for_san = game.board()
    for move in game.mainline_moves():
        san_moves_list.append(board_for_san.san(move))
        board_for_san.push(move)
    pgn_moves_text = " ".join(san_moves_list)
    
    final_fen = game.end().board().fen()
    ply_count = game.end().board().ply()

    # Get FEN around move 10-15 (ply 20-30)
    mid_game_fen = None
    temp_board_mid = game.board()
    for i, move in enumerate(game.mainline_moves()):
        temp_board_mid.push(move)
        if 19 <= i <= 29: # Plies 20-30 (moves 10-15)
            mid_game_fen = temp_board_mid.fen()
            break
    if not mid_game_fen and ply_count > 0 : # if game is shorter than 10 moves, use final FEN
        mid_game_fen = final_fen

    # Determine opening name more robustly if not in header (optional, can be slow)
    # For now, relying on header or ECO. Can integrate with openings_loader logic later if needed.

    # Extract FEN for every ply
    fen_at_each_ply = []
    board_for_all_fens = game.board() # Start with the initial board setup
    # Optionally store starting FEN (ply 0)
    # fen_at_each_ply.append(board_for_all_fens.fen())
    for move in game.mainline_moves():
        board_for_all_fens.push(move)
        fen_at_each_ply.append(board_for_all_fens.fen())

    return {
        "white_player": white,
        "black_player": black,
        "white_elo": white_elo,
        "black_elo": black_elo,
        "white_title": white_title if white_title else None,
        "black_title": black_title if black_title else None,
        "white_fide_id": white_fide_id if white_fide_id else None,
        "black_fide_id": black_fide_id if black_fide_id else None,
        "event": event,
        "site": site,
        "round": round_num,
        "date_utc": parsed_date.isoformat() + "Z" if parsed_date else None,
        "event_date": parsed_event_date.isoformat() + "Z" if parsed_event_date else None,
        "result": result,
        "eco": eco,
        "opening_name": opening_name_header, # Use header for now
        "ply_count": ply_count,
        "final_fen": final_fen,
        "mid_game_fen": mid_game_fen,
        "pgn_moves": pgn_moves_text,
        "all_ply_fens": fen_at_each_ply, # New field
        "type": "chess_game",
        "source_file": source_file_name,
    }

def load_pgn_games_to_weaviate():
    """Loads PGN games from the configured directory into Weaviate."""
    client = get_weaviate_client()
    if not client:
        print("ERROR: [GamesLoader] Cannot connect to Weaviate. Aborting PGN loading.")
        return

    # Force re-creation logic
    if os.getenv("FORCE_RECREATE_CHESSGAME_COLLECTION", "false").lower() == "true":
        if client.collections.exists(COLLECTION_NAME):
            print(f"INFO: [GamesLoader] FORCE_RECREATE_CHESSGAME_COLLECTION is true. Deleting existing collection: {COLLECTION_NAME}")
            client.collections.delete(COLLECTION_NAME)
            print(f"INFO: [GamesLoader] Collection {COLLECTION_NAME} deleted successfully.")

    create_chess_game_collection_if_not_exists(client)
    games_collection = client.collections.get(COLLECTION_NAME)

    if not os.path.exists(PGN_DIRECTORY):
        print(f"ERROR: [GamesLoader] PGN directory not found: {PGN_DIRECTORY}")
        os.makedirs(PGN_DIRECTORY, exist_ok=True)
        print(f"INFO: [GamesLoader] Created PGN directory: {PGN_DIRECTORY}. Please add PGN files there.")
        return

    pgn_files = [f for f in os.listdir(PGN_DIRECTORY) if f.lower().endswith(".pgn")]
    print(f"INFO: [GamesLoader] Found {len(pgn_files)} PGN files in {PGN_DIRECTORY}.")
    if not pgn_files:
        print(f"INFO: [GamesLoader] No PGN files to process in {PGN_DIRECTORY}.")
        return

    total_games_processed = 0
    total_games_imported = 0
    total_errors = 0

    # Configure batching
    with games_collection.batch.dynamic() as batch: # Dynamic batching handles size/timing
        for pgn_file_name in pgn_files:
            file_path = os.path.join(PGN_DIRECTORY, pgn_file_name)
            print(f"INFO: [GamesLoader] Processing file: {file_path}")
            games_in_current_file = 0
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as pgn_handle:
                    while True:
                        try:
                            game = chess.pgn.read_game(pgn_handle)
                            if game is None:
                                break # End of file or no more games
                            
                            total_games_processed += 1
                            parsed_game_data = parse_pgn_game(game, pgn_file_name)
                            
                            if parsed_game_data:
                                # Create a deterministic UUID based on key game headers
                                uuid_src_string = f"{parsed_game_data['white_player']}_{parsed_game_data['black_player']}_{parsed_game_data.get('date_utc', '')}_{parsed_game_data['event']}_{pgn_file_name}"
                                game_uuid = generate_uuid5(uuid_src_string)
                                
                                # Filter out None values before sending to Weaviate
                                properties_to_load = {k: v for k, v in parsed_game_data.items() if v is not None}

                                batch.add_object(
                                    properties=properties_to_load,
                                    uuid=game_uuid 
                                )
                                games_in_current_file += 1
                                total_games_imported +=1

                                if games_in_current_file % BATCH_SIZE == 0:
                                    print(f"DEBUG: [GamesLoader] Processed {games_in_current_file} games from {pgn_file_name} (Total processed: {total_games_processed}, Batch flushed if full/timed out).")

                        except Exception as e_game:
                            print(f"ERROR: [GamesLoader] Failed to parse or add a game from {pgn_file_name} (offset: {pgn_handle.tell()}): {e_game}")
                            total_errors +=1
                            # Skip to next game, attempt to continue
                            # chess.pgn.read_game can raise various errors on malformed PGNs
                            # We might need a more robust way to skip malformed game entries
                            try:
                                # Try to find next game header or skip a chunk of bytes
                                line = pgn_handle.readline()
                                while line and not line.startswith('[Event '):
                                    line = pgn_handle.readline()
                                if line: # Found next potential game
                                     # We need to "put back" this line or adjust parser. For now, just log.
                                     print(f"DEBUG: [GamesLoader] Attempting to recover by seeking to next [Event] in {pgn_file_name}")
                            except Exception as e_skip:
                                print(f"ERROR: [GamesLoader] Further error while trying to skip bad game in {pgn_file_name}: {e_skip}. Moving to next file.")
                                break # Move to next file

            except Exception as e_file:
                print(f"ERROR: [GamesLoader] Could not process file {file_path}: {e_file}")
                total_errors +=1
            
            print(f"INFO: [GamesLoader] Finished processing {pgn_file_name}. Imported {games_in_current_file} games from this file.")
            # Access failed objects through the collection's batch attribute
            if games_collection.batch.failed_objects: 
                 print(f"WARNING: [GamesLoader] {len(games_collection.batch.failed_objects)} objects failed to import in the last batch operation from file {pgn_file_name}.")
                 for failed_obj in games_collection.batch.failed_objects:
                     print(f"  - Failed object Original UUID: {failed_obj.original_uuid if hasattr(failed_obj, 'original_uuid') else 'N/A'}, Error: {failed_obj.message}")
                     total_errors += 1
                     total_games_imported -=1
                 # games_collection.batch.failed_objects.clear() # Optional: clear after logging


    # Final check on batch errors after loop (dynamic batch might have uncommitted objects)
    if games_collection.batch.failed_objects:
        print(f"WARNING: [GamesLoader] {len(games_collection.batch.failed_objects)} objects failed to import in the final batch operations.")
        for failed_obj in games_collection.batch.failed_objects:
            print(f"  - Failed object Original UUID: {failed_obj.original_uuid if hasattr(failed_obj, 'original_uuid') else 'N/A'}, Error: {failed_obj.message}")
            total_errors += 1
            total_games_imported -=1

    print(f"--- PGN Loading Summary ---")
    print(f"Total PGN files found: {len(pgn_files)}")
    print(f"Total games processed: {total_games_processed}")
    print(f"Total games successfully imported: {total_games_imported}")
    print(f"Total errors encountered: {total_errors}")
    print(f"--------------------------")

    if client:
        # client.close() removed - Weaviate client manages connections automatically
        print("DEBUG: [GamesLoader] Weaviate client closed.")

if __name__ == "__main__":
    print("Starting PGN Games Loader ETL script...")
    # Ensure PGN directory exists (or create it)
    if not os.path.exists(PGN_DIRECTORY):
        os.makedirs(PGN_DIRECTORY, exist_ok=True)
        print(f"INFO: Created PGN directory: {PGN_DIRECTORY}")
        print(f"Please place your TWIC PGN files in this directory before running again to load them.")
    
    load_pgn_games_to_weaviate()
    print("PGN Games Loader ETL script finished.") 