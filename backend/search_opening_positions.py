#!/usr/bin/env python3

import weaviate
import weaviate.classes.query as weaviate_query

client = weaviate.connect_to_local()

try:
    positions_collection = client.collections.get('ChessPositions')
    
    # Search for the specific FEN from the user's query
    test_fen = "r1bqk1nr/pppp1ppp/2n5/2b5/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5"
    print(f"=== Searching for specific FEN ===")
    print(f"Target FEN: {test_fen}")
    
    position_results = positions_collection.query.fetch_objects(
        filters=weaviate_query.Filter.by_property("fen").equal(test_fen),
        limit=10,
        return_properties=["fen", "game_ids", "occurrence_count", "white_win_rate", "most_common_eco", "opening_names"]
    )
    
    print(f"Found {len(position_results.objects) if position_results.objects else 0} exact matches")
    
    if position_results and position_results.objects:
        for i, pos_obj in enumerate(position_results.objects):
            props = pos_obj.properties
            print(f"  Match {i+1}:")
            print(f"    FEN: {props.get('fen', 'N/A')}")
            print(f"    Game IDs: {len(props.get('game_ids', []))} games")
            print(f"    Occurrence count: {props.get('occurrence_count', 0)}")
            print(f"    ECO: {props.get('most_common_eco', 'N/A')}")
            print(f"    Opening names: {props.get('opening_names', [])}")
    
    # Search for starting position
    print(f"\n=== Searching for starting position ===")
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    print(f"Target FEN: {starting_fen}")
    
    starting_results = positions_collection.query.fetch_objects(
        filters=weaviate_query.Filter.by_property("fen").equal(starting_fen),
        limit=5,
        return_properties=["fen", "game_ids", "occurrence_count", "most_common_eco"]
    )
    
    print(f"Found {len(starting_results.objects) if starting_results.objects else 0} starting position matches")
    
    if starting_results and starting_results.objects:
        for i, pos_obj in enumerate(starting_results.objects):
            props = pos_obj.properties
            print(f"  Match {i+1}:")
            print(f"    Game IDs: {len(props.get('game_ids', []))} games")
            print(f"    Occurrence count: {props.get('occurrence_count', 0)}")
    
    # Search for positions with low move numbers (opening positions)
    print(f"\n=== Searching for opening positions (move 1-10) ===")
    opening_results = positions_collection.query.fetch_objects(
        filters=weaviate_query.Filter.by_property("move_numbers").contains_any([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        limit=20,
        return_properties=["fen", "game_ids", "occurrence_count", "move_numbers", "most_common_eco", "opening_names"]
    )
    
    print(f"Found {len(opening_results.objects) if opening_results.objects else 0} opening positions")
    
    if opening_results and opening_results.objects:
        for i, pos_obj in enumerate(opening_results.objects[:5]):  # Show first 5
            props = pos_obj.properties
            moves = props.get('move_numbers', [])
            min_move = min(moves) if moves else 0
            print(f"  Opening {i+1}:")
            print(f"    FEN: {props.get('fen', 'N/A')}")
            print(f"    Min move number: {min_move}")
            print(f"    Games: {len(props.get('game_ids', []))}")
            print(f"    ECO: {props.get('most_common_eco', 'N/A')}")

finally:
    # client.close() removed - Weaviate client manages connections automatically 