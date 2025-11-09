#!/usr/bin/env python3

import weaviate
import chess
import chess.pgn
import datetime

def test_single_game():
    """Test loading a single game to debug the issue."""
    
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
        print("✅ Connected to Weaviate")
        
        if not client.collections.exists("ChessGame"):
            print("❌ ChessGame collection does not exist")
            return
        
        collection = client.collections.get("ChessGame")
        print("✅ Got ChessGame collection")
        
        # Read first game from PGN
        with open("data/twic_pgn/twic1590.pgn", 'r') as f:
            game = chess.pgn.read_game(f)
            if not game:
                print("❌ Could not read game from PGN")
                return
        
        print("✅ Read game from PGN")
        
        # Simple game data
        headers = game.headers
        game_data = {
            "white_player": headers.get("White", "Unknown"),
            "black_player": headers.get("Black", "Unknown"),
            "event": headers.get("Event", "Unknown"),
            "result": headers.get("Result", "*"),
            "type": "chess_game",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        
        print(f"✅ Parsed game data: {game_data}")
        
        # Try to insert single object
        uuid = weaviate.util.generate_uuid5("test_game_1")
        
        try:
            result = collection.data.insert(
                properties=game_data,
                uuid=uuid
            )
            print(f"✅ Inserted game with UUID: {result}")
        except Exception as e:
            print(f"❌ Error inserting game: {e}")
            return
        
        # Check count
        try:
            count = collection.aggregate.over_all(total_count=True).total_count
            print(f"✅ Total games in database: {count}")
        except Exception as e:
            print(f"❌ Error counting games: {e}")
        
        # client.close() removed - Weaviate client manages connections automatically
        print("✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_game() 