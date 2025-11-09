#!/usr/bin/env python3
"""
Recreate ChessGame Collection with Correct API Key
=================================================

The ChessGame collection was created with a hardcoded wrong API key.
This script deletes it and recreates with the correct key from .env.
"""

import os
import weaviate
from weaviate.collections.classes.config import Configure, Property, DataType, Tokenization

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    # Manual .env loading as fallback
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print("✅ Manually loaded .env file")

def recreate_chessgame_collection():
    """Delete and recreate ChessGame collection with correct API key."""
    
    # Get OpenAI API key from environment
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        return False
    
    print(f"✅ Using OpenAI API key: {openai_key[:20]}...")
    
    headers = {"X-OpenAI-Api-Key": openai_key}
    
    try:
        # Connect to Weaviate
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True
        )
        print("✅ Connected to Weaviate successfully")
        
        collection_name = "ChessGame"
        
        # Check if collection exists and delete it
        if client.collections.exists(collection_name):
            print(f"🗑️  Deleting existing collection '{collection_name}'...")
            client.collections.delete(collection_name)
            print("✅ Collection deleted successfully")
        else:
            print(f"ℹ️  Collection '{collection_name}' does not exist")
        
        # Create new collection with correct API key
        print(f"🏗️  Creating new collection '{collection_name}' with correct API key...")
        
        client.collections.create(
            name=collection_name,
            description="Chess games with metadata and moves, sourced from PGN files (e.g., TWIC).",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-small", 
                vectorize_collection_name=False
            ),
            properties=[
                # Basic game info
                Property(name="white_player", data_type=DataType.TEXT, description="Name of the white player.", tokenization=Tokenization.WORD),
                Property(name="black_player", data_type=DataType.TEXT, description="Name of the black player.", tokenization=Tokenization.WORD),
                Property(name="event", data_type=DataType.TEXT, description="Name of the tournament or event.", tokenization=Tokenization.WORD),
                Property(name="site", data_type=DataType.TEXT, description="Location of the event.", tokenization=Tokenization.WORD),
                Property(name="round", data_type=DataType.TEXT, description="Round number or identifier.", tokenization=Tokenization.FIELD),
                Property(name="result", data_type=DataType.TEXT, description="Result of the game (1-0, 0-1, 1/2-1/2, *).", tokenization=Tokenization.FIELD),
                Property(name="date", data_type=DataType.TEXT, description="Date of the game in PGN format.", tokenization=Tokenization.FIELD),
                Property(name="source_file", data_type=DataType.TEXT, description="Name of the PGN file source.", tokenization=Tokenization.FIELD),
                Property(name="moves", data_type=DataType.TEXT, description="Full PGN move text.", tokenization=Tokenization.WHITESPACE),
                
                # Optional fields
                Property(name="white_elo", data_type=DataType.NUMBER, description="ELO rating of the white player."),
                Property(name="black_elo", data_type=DataType.NUMBER, description="ELO rating of the black player."),
                Property(name="eco", data_type=DataType.TEXT, description="ECO code.", tokenization=Tokenization.FIELD),
                Property(name="opening", data_type=DataType.TEXT, description="Opening name.", tokenization=Tokenization.WORD),
                Property(name="time_control", data_type=DataType.TEXT, description="Time control.", tokenization=Tokenization.FIELD),
                Property(name="event_date", data_type=DataType.TEXT, description="Event date.", tokenization=Tokenization.FIELD),
                
                # FEN positions
                Property(name="starting_fen", data_type=DataType.TEXT, description="FEN of starting position.", tokenization=Tokenization.WHITESPACE),
                Property(name="ending_fen", data_type=DataType.TEXT, description="FEN of ending position.", tokenization=Tokenization.WHITESPACE),
                Property(name="move_count", data_type=DataType.NUMBER, description="Total number of moves."),
            ],
            inverted_index_config=Configure.inverted_index(
                bm25_k1=1.2,
                bm25_b=0.75,
            )
        )
        
        print(f"✅ Collection '{collection_name}' created successfully with correct API key!")
        
        # Verify the collection
        if client.collections.exists(collection_name):
            collection = client.collections.get(collection_name)
            print(f"📊 Collection verified and ready for use")
            return True
        else:
            print("❌ Collection verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Error recreating collection: {e}")
        return False
    finally:
        try:
            # client.close() removed - Weaviate client manages connections automatically
            print("🔌 Weaviate connection closed")
        except:
            pass

if __name__ == "__main__":
    print("🔄 RECREATING CHESSGAME COLLECTION WITH CORRECT API KEY")
    print("=" * 60)
    
    success = recreate_chessgame_collection()
    
    if success:
        print("\n🎉 SUCCESS! ChessGame collection recreated with correct API key")
        print("   You can now load TWIC files without API key errors")
    else:
        print("\n❌ FAILED to recreate collection")
    
    print("=" * 60) 