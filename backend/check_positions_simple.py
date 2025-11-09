#!/usr/bin/env python3

import weaviate

client = weaviate.connect_to_local()

try:
    positions_collection = client.collections.get('ChessPositions')
    results = positions_collection.query.fetch_objects(limit=20, return_properties=['fen', 'game_ids', 'occurrence_count'])
    
    print('=== First 20 positions in ChessPositions database ===')
    for i, obj in enumerate(results.objects):
        props = obj.properties
        fen = props.get("fen", "N/A")
        game_count = len(props.get("game_ids", []))
        occurrence = props.get("occurrence_count", 0)
        print(f'{i+1:2d}. {fen} (Games: {game_count}, Occurrences: {occurrence})')
    
    # Count total positions
    print(f'\n=== Database stats ===')
    # Try to get a count estimate
    all_results = positions_collection.query.fetch_objects(limit=100)
    print(f'Total positions found (sample): {len(all_results.objects)}')
    
finally:
    # client.close() removed - Weaviate client manages connections automatically 