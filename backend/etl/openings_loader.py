import weaviate
import requests
import csv # For TSV parsing
import chess # For FEN manipulation
import chess.pgn # For PGN to SAN conversion
import io # For handling string as file for PGN parsing
import os
import time
# Weaviate v4 imports
from weaviate.auth import AuthApiKey
from weaviate.collections.classes.config import Configure, Property, DataType, Tokenization
from weaviate.exceptions import WeaviateQueryException, WeaviateClosedClientError
from weaviate import ConnectionParams # Added for direct client instantiation

# --- Configuration ---
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080") # Used for connection
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY") # For Weaviate instances with auth
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # For text2vec-openai

TSV_BASE_URL = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/"
TSV_FILES = ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]
CLASS_NAME = "ChessOpening" # Will be used as collection name

# Weaviate v4 Collection Configuration
# Note: In v4, schema is often referred to as collection configuration.
OPENING_COLLECTION_CONFIG = {
    "name": CLASS_NAME,
    "description": "Represents a chess opening with its moves, FEN, ECO code, and other details.",
    "vectorizer_config": Configure.Vectorizer.text2vec_openai(
        model="text-embedding-3-small", # Changed to an available model
        vectorize_collection_name=False
    ),
    "inverted_index_config": Configure.inverted_index(
        bm25_k1=1.2,
        bm25_b=0.75,
        cleanup_interval_seconds=60
    ),
    "properties": [
        Property(name="opening_name", data_type=DataType.TEXT, description="Standard name of the opening.", tokenization=Tokenization.WORD),
        Property(name="eco_code", data_type=DataType.TEXT, description="ECO classification code.", tokenization=Tokenization.FIELD),
        Property(name="uci_moves", data_type=DataType.TEXT, description="Move sequence in UCI format.", tokenization=Tokenization.WHITESPACE),
        Property(name="san_moves", data_type=DataType.TEXT, description="Move sequence in SAN format.", tokenization=Tokenization.WHITESPACE),
        Property(name="pgn_moves", data_type=DataType.TEXT, description="Original PGN moves from source.", tokenization=Tokenization.WHITESPACE),
        Property(name="fen", data_type=DataType.TEXT, description="FEN of the resulting position after all UCI moves.", tokenization=Tokenization.WHITESPACE),
        Property(name="fen_before_last_move", data_type=DataType.TEXT, description="FEN of the position before the last UCI move.", tokenization=Tokenization.WHITESPACE),
        Property(name="normalized_fen_core", data_type=DataType.TEXT, description="FEN with only piece placement and side to move.", tokenization=Tokenization.WHITESPACE),
        Property(name="source", data_type=DataType.TEXT, description="Source of the opening data.", tokenization=Tokenization.FIELD),
        # Fields not populated from TSV, but defined if needed later:
        # Property(name="wikipedia_slug", data_type=DataType.TEXT, description="Wikipedia slug.", tokenization="keyword"),
        # Property(name="themes_and_plans", data_type=DataType.TEXT, description="General themes, strategic goals, and plans."),
        # Property(name="common_traps", data_type=DataType.TEXT, description="Common traps or tactical motifs."),
        # Property(name="popularity_score", data_type=DataType.NUMBER, description="A score indicating popularity.")
    ]
}

def get_weaviate_client_v4():
    """Initializes and returns a Weaviate v4 client."""
    headers = {}
    if OPENAI_API_KEY:
        headers["X-OpenAI-Api-Key"] = OPENAI_API_KEY
    
    auth_creds = AuthApiKey(api_key=WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None

    try:
        parsed_url = requests.utils.urlparse(WEAVIATE_URL)
        host = parsed_url.hostname
        port = parsed_url.port
        secure = parsed_url.scheme == "https"

        client = weaviate.WeaviateClient(
            connection_params=ConnectionParams.from_params(
                http_host=host,
                http_port=port,
                http_secure=secure,
                grpc_host=host,  # Assuming gRPC host is same as HTTP
                grpc_port=50051, # Default gRPC port for Weaviate
                grpc_secure=secure # Assuming gRPC security matches HTTP
            ),
            auth_client_secret=auth_creds,
            additional_headers=headers
        )
        
        client.connect()

        if not client.is_connected(): # is_connected() is the v4 check
            print(f"Weaviate client v4 not connected at {WEAVIATE_URL}. Check server and config.")
            # client.close() removed - Weaviate client manages connections automatically # Ensure client is closed if connection failed
            return None
        print(f"Successfully connected to Weaviate v4 at {WEAVIATE_URL}")
        return client
    except Exception as e:
        print(f"Error connecting to Weaviate v4: {e}")
        if 'client' in locals() and hasattr(client, 'is_connected') and client.is_connected():
            # client.close() removed - Weaviate client manages connections automatically
        return None

def download_and_parse_openings_data(base_url: str, tsv_files: list) -> list:
    """Downloads and parses openings data from multiple TSV files."""
    all_openings = []
    print("Downloading and parsing TSV data...")
    for tsv_filename in tsv_files:
        url = base_url + tsv_filename
        print(f"Processing {url}...")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            tsv_content = response.text
            reader = csv.reader(io.StringIO(tsv_content), delimiter='\t')
            
            count = 0
            for row_num, row in enumerate(reader):
                # Skip known header in e.tsv, or other potential headers if they only have 3 cols and look like it
                if row_num == 0 and len(row) <= 3 and "eco" in row[0].lower() and "name" in row[1].lower():
                    print(f"Skipping potential header row in {tsv_filename}: {row}")
                    continue
                
                if not row or not row[0]: # Skip empty rows or rows without an ECO code
                    print(f"Skipping empty or invalid row in {tsv_filename}: {row}")
                    continue

                data = {"eco": row[0]}
                data["name"] = row[1] if len(row) > 1 and row[1] else "Unnamed Opening"
                data["pgn"] = row[2] if len(row) > 2 and row[2] else ""
                data["uci"] = row[3] if len(row) > 3 and row[3] else ""
                data["epd"] = row[4] if len(row) > 4 and row[4] else "" # EPD not strictly needed if UCI->FEN works
                
                # If UCI is missing but PGN is present, try to generate UCI
                if not data["uci"] and data["pgn"]:
                    temp_board = chess.Board()
                    uci_moves_from_pgn = []
                    # PGN string might contain move numbers like "1. e4 e5"
                    # We need to feed SAN moves to board.parse_san()
                    # Splitting by space is naive; robust PGN parsing is complex for arbitrary PGN.
                    # Lichess PGNs are usually clean sequences of moves.
                    pgn_move_texts = data["pgn"].split()
                    
                    try:
                        for pgn_token in pgn_move_texts:
                            if pgn_token.endswith('.') or pgn_token.endswith('...'): # Skip "1.", "1..." 
                                continue
                            if not pgn_token: continue

                            # parse_san can fail if token is not a valid move in current position
                            move = temp_board.parse_san(pgn_token)
                            uci_moves_from_pgn.append(move.uci())
                            temp_board.push(move)
                        data["uci"] = " ".join(uci_moves_from_pgn)
                        # print(f"Derived UCI for {data['name']}: {data['uci']}")
                    except Exception: # Catch broad errors during PGN parsing (e.g., ValueError from parse_san)
                        # print(f"Could not derive UCI from PGN '{data['pgn']}' for {data['name']} ({data['eco']}): {e}")
                        # If UCI derivation fails, data["uci"] remains empty.
                        # load_openings_to_weaviate will skip if FEN generation fails due to empty UCI.
                        pass 
                
                all_openings.append(data)
                count += 1
            print(f"Successfully parsed and collected {count} entries from {tsv_filename}")

        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
        except csv.Error as e:
            print(f"Error parsing TSV content from {url}: {e}")
            
    if not all_openings:
        print("No opening data could be downloaded or parsed from any file.")
        return []
        
    print(f"Total collected entries from all TSV files: {len(all_openings)}")
    return all_openings

def create_opening_collection_if_not_exists_v4(client: weaviate.WeaviateClient, collection_config: dict):
    """Creates the ChessOpening collection in Weaviate v4 if it doesn't exist."""
    collection_name = collection_config["name"]
    try:
        if not client.collections.exists(collection_name):
            print(f"Collection '{collection_name}' does not exist. Creating...")
            # Convert Property objects in config to dicts for create_from_dict if that's how it's structured
            # Or use client.collections.create() with direct parameters
            
            # Simplified: create_from_dict expects a dict that matches its schema.
            # The OPENING_COLLECTION_CONFIG is already a dict, but properties are Property objects.
            # For create_from_dict, properties should also be dicts.
            
            # Alternative: use client.collections.create()
            client.collections.create(
                name=collection_config["name"],
                description=collection_config["description"],
                vectorizer_config=collection_config["vectorizer_config"],
                inverted_index_config=collection_config["inverted_index_config"],
                properties=collection_config["properties"] # Pass the list of Property objects directly
            )
            print(f"Collection '{collection_name}' created successfully.")
        else:
            print(f"Collection '{collection_name}' already exists.")
            # Add logic here if you want to check/update an existing collection
            # e.g., client.collections.update(...)
    except Exception as e:
        print(f"Error creating/checking collection '{collection_name}': {e}")
        raise

def pgn_to_san_list(pgn_moves_str: str, initial_board: chess.Board = None) -> list[str]:
    """Converts a PGN move string (e.g., '1. e4 e5 2. Nf3') to a list of SAN moves."""
    if not pgn_moves_str:
        return []
    
    board = initial_board.copy() if initial_board else chess.Board()
    san_moves = []
    
    # The PGNs in the dataset are just move sequences, often without full headers.
    # We simulate playing them on a board.
    # A simple split might work for Lichess format, but chess.pgn.read_game is safer if PGNs are complex.
    # However, Lichess PGNs are typically `1. e4 e5 2. Nf3 Nc6`
    
    # Simplistic parsing for "1. e4 e5" style PGNs.
    # This might need refinement if PGNs have comments or variations in the string.
    pgn_parts = pgn_moves_str.split()
    
    for part in pgn_parts:
        if part.endswith('.') or part.endswith('...'): # Skip move numbers like "1.", "1...", "1.e4" is not handled by this
            continue
        try:
            # Attempt to parse as SAN directly, as the board tracks context.
            move = board.parse_san(part)
            san_moves.append(board.san(move)) # Get standardized SAN
            board.push(move)
        except ValueError: # If parse_san fails, it might be an issue with the PGN part or board state
            # print(f"Warning: Could not parse SAN move '{part}' from PGN '{pgn_moves_str}' on board {board.fen()}. Skipping part.")
            # This can be noisy. If UCI moves are primary, this is secondary.
            pass # Silently skip parts that cannot be parsed as SAN for now
            
    return san_moves


def generate_fen_variants(uci_moves_str: str):
    """
    Generates the FEN for the final position, the position before the last move,
    and a core normalized FEN (piece placement and turn only).
    Returns (final_fen, fen_before_last, normalized_core_fen)
    Returns (None, None, None) on error.
    """
    if not uci_moves_str:
        return None, None, None
        
    board = chess.Board()
    moves = uci_moves_str.split(' ')
    
    fen_before_last = None
    
    try:
        for i, uci_move_str in enumerate(moves):
            if not uci_move_str: continue # Skip empty strings if any
            move = chess.Move.from_uci(uci_move_str)
            if move in board.legal_moves:
                if i == len(moves) - 1: # Just before making the last move
                    fen_before_last = board.fen()
                board.push(move)
            else:
                print(f"Warning: Illegal UCI move '{uci_move_str}' in sequence '{uci_moves_str}' for board {board.fen()}. Skipping sequence.")
                return None, None, None 
        
        final_fen = board.fen()
        normalized_core_fen = " ".join(final_fen.split(' ')[:2])
        
        return final_fen, fen_before_last, normalized_core_fen
    except ValueError as e: 
        print(f"Error processing UCI moves '{uci_moves_str}': {e}")
        return None, None, None


def load_openings_to_weaviate_v4(client: weaviate.WeaviateClient, collection_name: str, openings_data: list):
    """Loads parsed openings data into Weaviate v4 collection using batching."""
    if not openings_data:
        print("No openings data provided to load.")
        return

    try:
        openings_collection = client.collections.get(collection_name)
    except WeaviateQueryException as e: # Or other specific exception if collection doesn't exist
        print(f"Error getting collection '{collection_name}': {e}. Ensure it was created.")
        return
        
    imported_count = 0
    skipped_incomplete_data = 0
    error_count = 0

    print(f"Starting to process {len(openings_data)} opening entries for Weaviate collection '{collection_name}'...")

    with openings_collection.batch.dynamic() as batch: # Dynamic batching
        for i, entry in enumerate(openings_data):
            if i > 0 and i % 500 == 0:
                print(f"Processed {i}/{len(openings_data)} entries for batching...")

            uci_moves = entry.get("uci", "")
            pgn_moves_str = entry.get("pgn", "")
            opening_name = entry.get("name", "Unknown Opening")
            eco = entry.get("eco", "")

            final_fen_gen, fen_before_last_gen, normalized_fen_core_gen = generate_fen_variants(uci_moves)
            
            if not final_fen_gen:
                skipped_incomplete_data += 1
                continue
            
            san_moves_list = pgn_to_san_list(pgn_moves_str)
            san_moves_str = " ".join(san_moves_list) if san_moves_list else None

            properties_dict = {
                "opening_name": opening_name,
                "eco_code": eco,
                "uci_moves": uci_moves,
                "san_moves": san_moves_str,
                "pgn_moves": pgn_moves_str,
                "fen": final_fen_gen,
                "fen_before_last_move": fen_before_last_gen, 
                "normalized_fen_core": normalized_fen_core_gen,
                "source": "lichess_chess-openings_tsv_2024_v4",
            }
            
            # Filter out None values as Weaviate v4 might be stricter with property types
            # However, if a Property is defined as e.g. DataType.TEXT, it can accept None (will be omitted)
            # If a property is DataType.NUMBER and receives None, it might error if not explicitly allowed.
            # For TEXT types, None is usually fine. Let's try without explicit None filtering first.
            # properties_cleaned = {k: v for k, v in properties_dict.items() if v is not None and v != ""}

            try:
                batch.add_object(properties=properties_dict) # No explicit class_name here
                imported_count += 1
            except Exception as e: # Catch broad exceptions during batch add
                print(f"Error adding data object for '{opening_name}' to batch: {e}")
                # print(f"Data: {properties_dict}") # Careful, can be verbose
                error_count +=1
    
    print(f"Finished processing and batching {imported_count} openings.")
    if batch.number_errors > 0: # Check for batch errors
        print(f"Batch import had {batch.number_errors} errors.")
        # Detailed errors might be in batch.errors or need specific handling based on client version
    
    print(f"Successfully batched for import: {imported_count}")
    print(f"Skipped (incomplete data/FEN error): {skipped_incomplete_data}")
    print(f"Errors during batch add attempts (individual): {error_count}")


def main():
    """Main function to run the openings loader with Weaviate v4 client."""
    print("--- Starting Chess Openings ETL (TSV) for Weaviate v4 ---")
    
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY environment variable not set. text2vec-openai might fail if not configured globally in Weaviate.")

    all_openings_data = download_and_parse_openings_data(TSV_BASE_URL, TSV_FILES)
    if not all_openings_data:
        print("Failed to obtain and parse openings data. Exiting.")
        return

    client = None
    try:
        client = get_weaviate_client_v4()
        if not client:
            print("Failed to connect to Weaviate v4. Exiting.")
            return

        create_opening_collection_if_not_exists_v4(client, OPENING_COLLECTION_CONFIG)
        
        print(f"Loading {len(all_openings_data)} parsed opening entries into Weaviate collection '{CLASS_NAME}'...")
        start_time = time.time()
        load_openings_to_weaviate_v4(client, CLASS_NAME, all_openings_data)
        end_time = time.time()
        print(f"Data loading process (batching) took {end_time - start_time:.2f} seconds.")
    
    except WeaviateClosedClientError:
        print("Weaviate client was closed unexpectedly.")
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
    finally:
        if client:
            print("Closing Weaviate client.")
            # client.close() removed - Weaviate client manages connections automatically
    
    print("--- Chess Openings ETL (TSV) for Weaviate v4 Finished ---")

if __name__ == "__main__":
    # Make sure this script is in a directory that can import other ETL modules if needed,
    # or adjust Python path. For now, it's standalone.
    # Example: If this is in mvp1/backend/etl/openings_loader.py
    # and you run it from mvp1/backend directory: python -m etl.openings_loader
    main() 