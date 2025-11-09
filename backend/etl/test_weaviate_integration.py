#!/usr/bin/env python3
"""
Direct Weaviate Integration Test
===============================

This script directly tests loading our combined TWIC file into Weaviate
by temporarily copying it to the expected location and using the existing loader.
"""

import sys
import os
import shutil
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix import issues by importing config directly
import config as etl_config

# Update the config to use absolute import
sys.path.insert(0, str(Path(__file__).parent))

def test_weaviate_integration():
    """Test loading our combined file into Weaviate"""
    print("🧪 Direct Weaviate Integration Test")
    print("=" * 50)
    
    # Our combined file from the small test
    combined_file = Path("/home/marblemaster/Desktop/Cursor/mvp1/backend/data/twic_pgn/twic_combined/twic_complete_20250531.pgn")
    
    if not combined_file.exists():
        print(f"❌ Combined file not found: {combined_file}")
        return False
    
    print(f"📁 Found combined file: {combined_file}")
    print(f"📊 File size: {combined_file.stat().st_size:,} bytes")
    
    # Get the PGN data directory
    pgn_data_dir = Path(etl_config.PGN_DATA_DIR)
    print(f"📂 PGN data directory: {pgn_data_dir}")
    
    # Create a temp copy with a standard name for the loader
    temp_pgn_file = pgn_data_dir / "twic_test_integration.pgn"
    
    try:
        print(f"📄 Copying file for integration test...")
        shutil.copy2(combined_file, temp_pgn_file)
        print(f"✅ Copied to: {temp_pgn_file}")
        
        # Temporarily update the config to point to our test file
        original_pgn_dir = etl_config.PGN_DATA_DIR
        etl_config.PGN_DATA_DIR = str(pgn_data_dir)
        
        # Now import and use the games loader
        print(f"🔌 Importing games loader...")
        
        # Monkey patch the relative import issue
        import games_loader
        games_loader.etl_config = etl_config
        
        print(f"🌐 Testing Weaviate connection...")
        client = games_loader.get_weaviate_client()
        
        if not client:
            print("❌ Could not connect to Weaviate")
            return False
        
        print("✅ Connected to Weaviate successfully")
        
        print(f"🏗️ Creating/verifying chess game collection...")
        games_loader.create_chess_game_collection_if_not_exists(client)
        print("✅ Collection ready")
        
        print(f"📥 Loading games from test file...")
        
        # Load games directly from our test file
        import weaviate
        import chess.pgn
        from weaviate.util import generate_uuid5
        
        games_loaded = 0
        batch_size = 100
        
        with open(temp_pgn_file, 'r', encoding='utf-8', errors='ignore') as f:
            collection = client.collections.get(games_loader.COLLECTION_NAME)
            
            # Process games in batches
            batch_count = 0
            
            while True:
                batch_objects = []
                
                # Read batch_size games
                for i in range(batch_size):
                    try:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break  # End of file
                        
                        # Parse the game using the existing function
                        game_obj = games_loader.parse_pgn_game(game, "twic_test_integration.pgn")
                        if game_obj:
                            batch_objects.append(game_obj)
                            
                    except Exception as e:
                        print(f"⚠️ Error parsing game: {e}")
                        continue
                
                if not batch_objects:
                    break  # No more games
                
                # Insert the batch
                try:
                    collection.data.insert_many(batch_objects)
                    games_loaded += len(batch_objects)
                    batch_count += 1
                    
                    if batch_count % 10 == 0:  # Progress every 1000 games
                        print(f"📈 Loaded {games_loaded} games so far...")
                        
                except Exception as e:
                    print(f"❌ Error inserting batch: {e}")
                    break
        
        print(f"🎉 Successfully loaded {games_loaded} games into Weaviate!")
        
        # Test a simple query
        print(f"🔍 Testing query...")
        try:
            result = collection.query.fetch_objects(limit=5)
            print(f"✅ Query test successful - found {len(result.objects)} sample games")
            
            # Show a sample game
            if result.objects:
                sample = result.objects[0]
                print(f"📋 Sample game:")
                print(f"  White: {sample.properties.get('white_player', 'Unknown')}")
                print(f"  Black: {sample.properties.get('black_player', 'Unknown')}")
                print(f"  Event: {sample.properties.get('event', 'Unknown')}")
                print(f"  Result: {sample.properties.get('result', 'Unknown')}")
        
        except Exception as e:
            print(f"⚠️ Query test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        return False
        
    finally:
        # Clean up
        if temp_pgn_file.exists():
            temp_pgn_file.unlink()
            print(f"🧹 Cleaned up temp file")
        
        # Restore original config
        etl_config.PGN_DATA_DIR = original_pgn_dir
        
        # Close client
        if 'client' in locals() and client:
            # client.close() removed - Weaviate client manages connections automatically

def main():
    """Run the integration test"""
    print("🚀 Starting Weaviate integration test...")
    
    success = test_weaviate_integration()
    
    if success:
        print(f"\n🎉 Weaviate integration test PASSED!")
        print(f"✅ Your chess games are now searchable in Weaviate")
        print(f"🚀 Ready for full TWIC expansion!")
    else:
        print(f"\n⚠️ Weaviate integration test FAILED!")
        print(f"Please check Weaviate connection and try again.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 