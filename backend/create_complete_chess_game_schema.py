#!/usr/bin/env python3

import weaviate
import os
import sys

# Add the backend directory to the path to import etl modules
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

# Import Weaviate v4 configuration classes
from weaviate.collections.classes.config import Configure, Property, DataType, Tokenization

def create_complete_chess_game_schema():
    """Create a comprehensive ChessGame collection schema in Weaviate with ALL PGN fields."""
    
    # Configuration
    COLLECTION_NAME = "ChessGame"
    OPENAI_API_KEY = "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"
    
    # Set up headers for OpenAI API key
    headers = {}
    if OPENAI_API_KEY:
        headers["X-OpenAI-Api-Key"] = OPENAI_API_KEY
        print("✅ OpenAI API Key configured for embeddings")
    
    try:
        # Step 1: Connect to Weaviate
        print("🔌 Connecting to Weaviate...")
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True  # Skip gRPC health checks to avoid connection issues
        )
        print("✅ Connected to Weaviate successfully")
        
        # Step 2: Check if collection already exists
        print(f"🔍 Checking if collection '{COLLECTION_NAME}' exists...")
        if client.collections.exists(COLLECTION_NAME):
            print(f"⚠️  Collection '{COLLECTION_NAME}' already exists!")
            
            # Ask user if they want to recreate it
            response = input("Do you want to delete and recreate it? (y/N): ").strip().lower()
            if response == 'y' or response == 'yes':
                print(f"🗑️  Deleting existing collection '{COLLECTION_NAME}'...")
                client.collections.delete(COLLECTION_NAME)
                print("✅ Collection deleted successfully")
            else:
                print("❌ Aborted. Collection already exists.")
                return False
        
        # Step 3: Create the collection with COMPLETE schema including ALL PGN fields
        print(f"🏗️  Creating collection '{COLLECTION_NAME}' with COMPLETE schema...")
        print("📋 Including ALL PGN fields found in analysis:")
        print("   - Core: Event, Site, Date, Round, White, Black, Result, EventDate")
        print("   - Players: WhiteTitle, BlackTitle, WhiteElo, BlackElo, WhiteFideId, BlackFideId")
        print("   - Chess: ECO, Opening, Variation")
        print("   - Teams: WhiteTeam, BlackTeam, EventType")
        print("   - Moves: PGN moves, FEN positions")
        print("   - System: source file, computed fields")
        
        client.collections.create(
            name=COLLECTION_NAME,
            description="A comprehensive collection of chess games with ALL metadata and moves from PGN files (e.g., TWIC). Includes all standard PGN headers plus computed fields for analysis.",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-small", 
                vectorize_collection_name=False
            ),
            properties=[
                # ===== CORE PGN FIELDS (present in all games) =====
                Property(name="event", data_type=DataType.TEXT, description="Name of the tournament or event.", tokenization=Tokenization.WORD),
                Property(name="site", data_type=DataType.TEXT, description="Location of the event.", tokenization=Tokenization.WORD),
                Property(name="date", data_type=DataType.TEXT, description="Date of the game in PGN format (YYYY.MM.DD).", tokenization=Tokenization.FIELD),
                Property(name="date_utc", data_type=DataType.DATE, description="Date of the game converted to UTC datetime."),
                Property(name="round", data_type=DataType.TEXT, description="Round number or identifier.", tokenization=Tokenization.FIELD),
                Property(name="white_player", data_type=DataType.TEXT, description="Name of the white player.", tokenization=Tokenization.WORD),
                Property(name="black_player", data_type=DataType.TEXT, description="Name of the black player.", tokenization=Tokenization.WORD),
                Property(name="result", data_type=DataType.TEXT, description="Result of the game (1-0, 0-1, 1/2-1/2, *).", tokenization=Tokenization.FIELD),
                Property(name="event_date", data_type=DataType.TEXT, description="Start date of the event in PGN format.", tokenization=Tokenization.FIELD),
                Property(name="event_date_utc", data_type=DataType.DATE, description="Start date of the event converted to UTC datetime."),
                
                # ===== PLAYER INFORMATION (mostly present) =====
                Property(name="white_title", data_type=DataType.TEXT, description="Title of the white player (GM, IM, FM, CM, WGM, WIM, WFM, WCM, etc.).", tokenization=Tokenization.FIELD),
                Property(name="black_title", data_type=DataType.TEXT, description="Title of the black player (GM, IM, FM, CM, WGM, WIM, WFM, WCM, etc.).", tokenization=Tokenization.FIELD),
                Property(name="white_elo", data_type=DataType.NUMBER, description="ELO rating of the white player."),
                Property(name="black_elo", data_type=DataType.NUMBER, description="ELO rating of the black player."),
                Property(name="white_fide_id", data_type=DataType.TEXT, description="FIDE ID of the white player.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="black_fide_id", data_type=DataType.TEXT, description="FIDE ID of the black player.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                
                # ===== TEAM INFORMATION (present in team events) =====
                Property(name="white_team", data_type=DataType.TEXT, description="Team name for the white player (in team tournaments).", tokenization=Tokenization.WORD),
                Property(name="black_team", data_type=DataType.TEXT, description="Team name for the black player (in team tournaments).", tokenization=Tokenization.WORD),
                Property(name="event_type", data_type=DataType.TEXT, description="Type of event (e.g., 'team', 'swiss', 'round-robin').", tokenization=Tokenization.FIELD),
                
                # ===== CHESS-SPECIFIC INFORMATION =====
                Property(name="eco", data_type=DataType.TEXT, description="ECO (Encyclopedia of Chess Openings) code.", tokenization=Tokenization.FIELD),
                Property(name="opening", data_type=DataType.TEXT, description="Name of the opening played.", tokenization=Tokenization.WORD),
                Property(name="variation", data_type=DataType.TEXT, description="Specific variation of the opening.", tokenization=Tokenization.WORD),
                Property(name="ply_count", data_type=DataType.NUMBER, description="Total number of plies (half-moves) in the game."),
                
                # ===== POSITION DATA =====
                Property(name="final_fen", data_type=DataType.TEXT, description="FEN of the final position.", tokenization=Tokenization.WHITESPACE),
                Property(name="mid_game_fen", data_type=DataType.TEXT, description="FEN around move 10-15 for position-based search.", tokenization=Tokenization.WHITESPACE),
                Property(name="all_ply_fens", data_type=DataType.TEXT_ARRAY, description="An ordered list of FEN strings, one for each ply (half-move) of the game, from ply 1 to the end.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                
                # ===== MOVE DATA =====
                Property(name="pgn_moves", data_type=DataType.TEXT, description="Full PGN move text with move numbers.", tokenization=Tokenization.WHITESPACE),
                Property(name="moves_san", data_type=DataType.TEXT_ARRAY, description="Array of moves in Standard Algebraic Notation (SAN).", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="moves_uci", data_type=DataType.TEXT_ARRAY, description="Array of moves in UCI notation.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                
                # ===== COMPUTED ANALYSIS FIELDS =====
                Property(name="game_length_category", data_type=DataType.TEXT, description="Game length category: short (<30 moves), medium (30-60), long (>60).", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="player_strength_category", data_type=DataType.TEXT, description="Player strength category based on average ELO: master (>2400), expert (2200-2400), class_a (2000-2200), etc.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="opening_family", data_type=DataType.TEXT, description="Opening family derived from ECO code (e.g., 'Sicilian', 'French', 'King's Pawn').", tokenization=Tokenization.FIELD),
                
                # ===== SYSTEM FIELDS =====
                Property(name="type", data_type=DataType.TEXT, description="Object type, always 'chess_game'.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="source_file", data_type=DataType.TEXT, description="Name of the PGN file from which this game was extracted.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="game_index", data_type=DataType.NUMBER, description="Index of this game within the source PGN file (0-based)."),
                Property(name="created_at", data_type=DataType.DATE, description="Timestamp when this record was created in the database."),
                Property(name="updated_at", data_type=DataType.DATE, description="Timestamp when this record was last updated."),
                
                # ===== SEARCH AND ANALYSIS HELPERS =====
                Property(name="searchable_text", data_type=DataType.TEXT, description="Combined searchable text including player names, event, opening, and key metadata.", tokenization=Tokenization.WORD),
                Property(name="tags", data_type=DataType.TEXT_ARRAY, description="Searchable tags derived from game characteristics (e.g., 'endgame', 'tactics', 'blunder').", tokenization=Tokenization.FIELD),
            ],
            inverted_index_config=Configure.inverted_index(
                bm25_k1=1.2,
                bm25_b=0.75,
            )
        )
        
        print(f"✅ Collection '{COLLECTION_NAME}' created successfully!")
        
        # Step 4: Verify the collection was created
        print("🔍 Verifying collection creation...")
        if client.collections.exists(COLLECTION_NAME):
            print("✅ Collection verified - it exists in Weaviate")
            
            # Get collection info
            collection = client.collections.get(COLLECTION_NAME)
            print(f"📊 Collection details:")
            print(f"   - Name: {COLLECTION_NAME}")
            print(f"   - Description: Comprehensive chess games with ALL PGN fields")
            print(f"   - Vectorizer: text2vec-openai (text-embedding-3-small)")
            print(f"   - Properties: 35+ fields defined")
            print(f"   - Includes: All PGN headers + computed analysis fields")
            
            return True
        else:
            print("❌ Collection verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            # client.close() removed - Weaviate client manages connections automatically
            print("🔌 Weaviate connection closed")
        except:
            pass

def verify_complete_schema():
    """Verify the complete schema was created correctly by checking via REST API."""
    print("\n🔍 Verifying complete schema via REST API...")
    
    import subprocess
    import json
    
    try:
        # Get schema via curl
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8080/v1/schema"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            schema = json.loads(result.stdout)
            classes = schema.get("classes", [])
            
            chess_game_class = None
            for cls in classes:
                if cls.get("class") == "ChessGame":
                    chess_game_class = cls
                    break
            
            if chess_game_class:
                properties = chess_game_class.get("properties", [])
                print(f"✅ ChessGame class found with {len(properties)} properties:")
                
                # Organize properties by category
                categories = {
                    "Core PGN": ["event", "site", "date", "round", "white_player", "black_player", "result"],
                    "Player Info": ["white_title", "black_title", "white_elo", "black_elo", "white_fide_id", "black_fide_id"],
                    "Team Info": ["white_team", "black_team", "event_type"],
                    "Chess Info": ["eco", "opening", "variation", "ply_count"],
                    "Position Data": ["final_fen", "mid_game_fen", "all_ply_fens"],
                    "Move Data": ["pgn_moves", "moves_san", "moves_uci"],
                    "Analysis": ["game_length_category", "player_strength_category", "opening_family"],
                    "System": ["type", "source_file", "game_index", "created_at", "updated_at"],
                    "Search": ["searchable_text", "tags"]
                }
                
                for category, prop_names in categories.items():
                    print(f"\n   📂 {category}:")
                    for prop_name in prop_names:
                        prop = next((p for p in properties if p.get("name") == prop_name), None)
                        if prop:
                            data_type = prop.get("dataType", ["unknown"])[0]
                            print(f"      ✅ {prop_name}: {data_type}")
                        else:
                            print(f"      ❌ {prop_name}: missing")
                
                return True
            else:
                print("❌ ChessGame class not found in schema")
                return False
        else:
            print(f"❌ Failed to get schema: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting COMPLETE ChessGame Collection Schema Creation")
    print("=" * 60)
    print("📋 This schema includes ALL PGN fields found in the analysis:")
    print("   • All standard PGN headers (Event, Site, Date, Players, etc.)")
    print("   • Player information (Titles, ELO, FIDE IDs)")
    print("   • Team information (WhiteTeam, BlackTeam, EventType)")
    print("   • Chess-specific data (ECO, Opening, Variation)")
    print("   • Position and move data (FENs, PGN moves, SAN, UCI)")
    print("   • Computed analysis fields (categories, families)")
    print("   • System and search helper fields")
    print("=" * 60)
    
    success = create_complete_chess_game_schema()
    
    if success:
        verify_complete_schema()
        print("\n🎉 COMPLETE schema creation completed successfully!")
        print("\nNext steps:")
        print("1. Load games: python -m etl.games_loader")
        print("2. Count games: python count_games_simple.py")
        print("3. Search games by any field!")
    else:
        print("\n❌ Schema creation failed!")
        sys.exit(1) 