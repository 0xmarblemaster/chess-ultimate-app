#!/usr/bin/env python3

from etl.weaviate_loader import get_weaviate_client

def examine_game_fens():
    """Examine how FENs are stored in ChessGame objects."""
    client = get_weaviate_client()
    if not client:
        print('Could not connect to Weaviate')
        return
    
    try:
        games_collection = client.collections.get('ChessGame')
        
        # Get a sample game to examine its structure
        response = games_collection.query.fetch_objects(limit=1)
        if response.objects:
            game = response.objects[0]
            props = game.properties
            
            print("=== ChessGame Data Structure ===\n")
            print(f"Game: {props.get('white_player')} vs {props.get('black_player')}")
            print(f"UUID: {str(game.uuid)}")
            print(f"\nAvailable properties:")
            for key, value in props.items():
                if 'fen' in key.lower():
                    print(f"  🎯 {key}: {type(value)} - {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
                else:
                    print(f"  • {key}: {type(value)}")
            
            # Check if all_ply_fens exists and examine its structure
            if 'all_ply_fens' in props:
                all_fens = props['all_ply_fens']
                print(f"\n=== all_ply_fens Analysis ===")
                print(f"Type: {type(all_fens)}")
                print(f"Length: {len(all_fens) if hasattr(all_fens, '__len__') else 'N/A'}")
                if hasattr(all_fens, '__len__') and len(all_fens) > 0:
                    print(f"First FEN: {all_fens[0]}")
                    print(f"Last FEN: {all_fens[-1]}")
                    if len(all_fens) > 2:
                        print(f"Middle FEN: {all_fens[len(all_fens)//2]}")
                        
        # Test a specific FEN search
        test_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3"
        print(f"\n=== Testing FEN Search ===")
        print(f"Searching for: {test_fen}")
        
        # Search by exact FEN match in all_ply_fens
        from weaviate.collections.classes.filters import Filter
        response = games_collection.query.fetch_objects(
            filters=Filter.by_property("all_ply_fens").contains_any([test_fen]),
            limit=5
        )
        
        print(f"Found {len(response.objects)} games with this exact FEN")
        for i, game in enumerate(response.objects, 1):
            props = game.properties
            print(f"  {i}. {props.get('white_player')} vs {props.get('black_player')} ({str(game.uuid)})")
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        if client:
            # client.close() removed - Weaviate client manages connections automatically

if __name__ == '__main__':
    examine_game_fens() 