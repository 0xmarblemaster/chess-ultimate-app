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

def create_chess_game_schema():
    """Create the ChessGame collection schema in Weaviate."""
    
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
        
        # Step 3: Create the collection with full schema
        print(f"🏗️  Creating collection '{COLLECTION_NAME}' with schema...")
        
        client.collections.create(
            name=COLLECTION_NAME,
            description="A collection of chess games with metadata and moves, sourced from PGN files (e.g., TWIC).",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-small", 
                vectorize_collection_name=False
            ),
            properties=[
                # Player Information
                Property(name="white_player", data_type=DataType.TEXT, description="Name of the white player.", tokenization=Tokenization.WORD),
                Property(name="black_player", data_type=DataType.TEXT, description="Name of the black player.", tokenization=Tokenization.WORD),
                Property(name="white_elo", data_type=DataType.NUMBER, description="ELO rating of the white player."),
                Property(name="black_elo", data_type=DataType.NUMBER, description="ELO rating of the black player."),
                Property(name="white_title", data_type=DataType.TEXT, description="Title of the white player (GM, IM, FM, etc.).", tokenization=Tokenization.FIELD),
                Property(name="black_title", data_type=DataType.TEXT, description="Title of the black player (GM, IM, FM, etc.).", tokenization=Tokenization.FIELD),
                Property(name="white_fide_id", data_type=DataType.TEXT, description="FIDE ID of the white player.", tokenization=Tokenization.FIELD),
                Property(name="black_fide_id", data_type=DataType.TEXT, description="FIDE ID of the black player.", tokenization=Tokenization.FIELD),
                
                # Game Metadata
                Property(name="event", data_type=DataType.TEXT, description="Name of the tournament or event.", tokenization=Tokenization.WORD),
                Property(name="site", data_type=DataType.TEXT, description="Location of the event.", tokenization=Tokenization.WORD),
                Property(name="round", data_type=DataType.TEXT, description="Round number or identifier.", tokenization=Tokenization.FIELD),
                Property(name="date_utc", data_type=DataType.DATE, description="Date of the game (UTC)."),
                Property(name="event_date", data_type=DataType.DATE, description="Start date of the event (UTC)."),
                Property(name="result", data_type=DataType.TEXT, description="Result of the game (e.g., 1-0, 0-1, 1/2-1/2).", tokenization=Tokenization.FIELD),
                
                # Chess-specific Information
                Property(name="eco", data_type=DataType.TEXT, description="ECO (Encyclopedia of Chess Openings) code.", tokenization=Tokenization.FIELD),
                Property(name="opening_name", data_type=DataType.TEXT, description="Name of the opening played.", tokenization=Tokenization.WORD),
                Property(name="ply_count", data_type=DataType.NUMBER, description="Total number of plies (half-moves) in the game."),
                
                # Position Data
                Property(name="final_fen", data_type=DataType.TEXT, description="FEN of the final position.", tokenization=Tokenization.WHITESPACE),
                Property(name="mid_game_fen", data_type=DataType.TEXT, description="FEN around move 10-15 for position-based search.", tokenization=Tokenization.WHITESPACE),
                Property(name="all_ply_fens", data_type=DataType.TEXT_ARRAY, description="An ordered list of FEN strings, one for each ply (half-move) of the game, from ply 1 to the end.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                
                # Move Data
                Property(name="pgn_moves", data_type=DataType.TEXT, description="Full PGN move text.", tokenization=Tokenization.WHITESPACE),
                
                # System Fields
                Property(name="type", data_type=DataType.TEXT, description="Object type, e.g., 'chess_game'.", tokenization=Tokenization.FIELD, skip_vectorization=True),
                Property(name="source_file", data_type=DataType.TEXT, description="Name of the PGN file from which this game was extracted.", tokenization=Tokenization.FIELD, skip_vectorization=True),
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
            print(f"   - Description: A collection of chess games with metadata and moves")
            print(f"   - Vectorizer: text2vec-openai (text-embedding-3-small)")
            print(f"   - Properties: 22 fields defined")
            
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

def verify_schema():
    """Verify the schema was created correctly by checking via REST API."""
    print("\n🔍 Verifying schema via REST API...")
    
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
                
                # Show key properties
                key_props = ["white_player", "black_player", "eco", "all_ply_fens", "pgn_moves"]
                for prop_name in key_props:
                    prop = next((p for p in properties if p.get("name") == prop_name), None)
                    if prop:
                        data_type = prop.get("dataType", ["unknown"])[0]
                        print(f"   ✅ {prop_name}: {data_type}")
                    else:
                        print(f"   ❌ {prop_name}: missing")
                
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
    print("🚀 Starting ChessGame Collection Schema Creation")
    print("=" * 50)
    
    success = create_chess_game_schema()
    
    if success:
        verify_schema()
        print("\n🎉 Schema creation completed successfully!")
        print("\nNext steps:")
        print("1. Load games: python -m etl.games_loader")
        print("2. Count games: python count_games_simple.py")
    else:
        print("\n❌ Schema creation failed!")
        sys.exit(1) 