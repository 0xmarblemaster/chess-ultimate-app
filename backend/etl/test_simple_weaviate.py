#!/usr/bin/env python3
"""
Simple Weaviate Test without Vectorization
==========================================

This script tests loading our combined TWIC file into Weaviate
without OpenAI vectorization to focus on core functionality.
"""

import sys
import os
import shutil
from pathlib import Path
import weaviate
import chess.pgn
from weaviate.collections.classes.config import Configure, Property, DataType, Tokenization

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix import issues by importing config directly
import config as etl_config

def test_simple_weaviate():
    """Test loading games without vectorization"""
    print("🧪 Simple Weaviate Test (No Vectorization)")
    print("=" * 60)
    
    # Our combined file from the small test
    combined_file = Path("/home/marblemaster/Desktop/Cursor/mvp1/backend/data/twic_pgn/twic_combined/twic_complete_20250531.pgn")
    
    if not combined_file.exists():
        print(f"❌ Combined file not found: {combined_file}")
        return False
    
    print(f"📁 Found combined file: {combined_file}")
    file_size = combined_file.stat().st_size
    print(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
    
    try:
        print(f"🌐 Connecting to Weaviate...")
        
        # Connect to Weaviate without OpenAI
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers={}  # No OpenAI headers
        )
        
        if not client.is_ready():
            print("❌ Weaviate is not ready")
            return False
        
        print("✅ Connected to Weaviate successfully")
        
        # Create a simple collection name for testing
        collection_name = "TWICTestSimple"
        
        # Delete collection if it exists for clean test
        if client.collections.exists(collection_name):
            print(f"🗑️ Deleting existing collection: {collection_name}")
            client.collections.delete(collection_name)
        
        print(f"🏗️ Creating simple collection: {collection_name}")
        
        # Create collection without vectorization
        client.collections.create(
            name=collection_name,
            description="Simple TWIC chess games test collection without vectorization",
            vectorizer_config=Configure.Vectorizer.none(),  # No vectorization
            properties=[
                Property(name="white_player", data_type=DataType.TEXT, description="White player name", tokenization=Tokenization.FIELD),
                Property(name="black_player", data_type=DataType.TEXT, description="Black player name", tokenization=Tokenization.FIELD),
                Property(name="event", data_type=DataType.TEXT, description="Tournament event", tokenization=Tokenization.FIELD),
                Property(name="site", data_type=DataType.TEXT, description="Event location", tokenization=Tokenization.FIELD),
                Property(name="date_str", data_type=DataType.TEXT, description="Game date", tokenization=Tokenization.FIELD),
                Property(name="result", data_type=DataType.TEXT, description="Game result", tokenization=Tokenization.FIELD),
                Property(name="white_elo", data_type=DataType.NUMBER, description="White player ELO"),
                Property(name="black_elo", data_type=DataType.NUMBER, description="Black player ELO"),
                Property(name="eco", data_type=DataType.TEXT, description="ECO opening code", tokenization=Tokenization.FIELD),
                Property(name="moves_text", data_type=DataType.TEXT, description="Game moves", tokenization=Tokenization.FIELD),
            ]
        )
        
        print("✅ Collection created successfully")
        
        # Get the collection
        collection = client.collections.get(collection_name)
        
        print(f"📥 Loading games from combined file...")
        
        games_loaded = 0
        batch_size = 50  # Smaller batches for testing
        batch_objects = []
        
        with open(combined_file, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                try:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break  # End of file
                    
                    headers = game.headers
                    
                    # Extract basic information
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
                    
                    # Extract moves as text
                    moves = []
                    board = game.board()
                    for move in game.mainline_moves():
                        moves.append(board.san(move))
                        board.push(move)
                    moves_text = " ".join(moves)
                    
                    # Create simple game object
                    game_obj = {
                        "white_player": headers.get("White", "Unknown"),
                        "black_player": headers.get("Black", "Unknown"),
                        "event": headers.get("Event", "Unknown"),
                        "site": headers.get("Site", "?"),
                        "date_str": headers.get("Date", "????.??.??"),
                        "result": headers.get("Result", "*"),
                        "white_elo": white_elo,
                        "black_elo": black_elo,
                        "eco": headers.get("ECO", ""),
                        "moves_text": moves_text[:1000]  # Limit size
                    }
                    
                    batch_objects.append(game_obj)
                    
                    # Insert when batch is full
                    if len(batch_objects) >= batch_size:
                        collection.data.insert_many(batch_objects)
                        games_loaded += len(batch_objects)
                        batch_objects = []
                        
                        if games_loaded % 500 == 0:
                            print(f"📈 Loaded {games_loaded} games so far...")
                    
                except Exception as e:
                    print(f"⚠️ Error processing game: {e}")
                    continue
            
            # Insert remaining games
            if batch_objects:
                collection.data.insert_many(batch_objects)
                games_loaded += len(batch_objects)
        
        print(f"🎉 Successfully loaded {games_loaded} games into Weaviate!")
        
        # Test queries
        print(f"🔍 Testing basic queries...")
        
        # Test 1: Count all games
        result = collection.aggregate.over_all(total_count=True)
        total_count = result.total_count
        print(f"✅ Total games in collection: {total_count}")
        
        # Test 2: Get sample games
        result = collection.query.fetch_objects(limit=3)
        print(f"✅ Retrieved {len(result.objects)} sample games")
        
        for i, game in enumerate(result.objects, 1):
            props = game.properties
            print(f"  {i}. {props['white_player']} vs {props['black_player']}")
            print(f"     Event: {props['event']}")
            print(f"     Result: {props['result']}")
        
        # Test 3: Search for specific player
        result = collection.query.fetch_objects(
            where=weaviate.classes.query.Filter.by_property("white_player").contains_any(["Carlsen", "Kasparov", "Fischer"]),
            limit=5
        )
        print(f"✅ Found {len(result.objects)} games with famous players")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Close client
        if 'client' in locals() and client:
            # client.close() removed - Weaviate client manages connections automatically

def main():
    """Run the simple test"""
    print("🚀 Starting simple Weaviate test...")
    
    success = test_simple_weaviate()
    
    if success:
        print(f"\n🎉 Simple Weaviate test PASSED!")
        print(f"✅ Core functionality verified")
        print(f"🔄 Ready to proceed with full expansion")
    else:
        print(f"\n⚠️ Simple Weaviate test FAILED!")
        print(f"Please check the errors above")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 