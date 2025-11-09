#!/usr/bin/env python3

from etl.weaviate_loader import get_weaviate_client

def count_games():
    """Count the total number of games in the ChessGame collection."""
    client = get_weaviate_client()
    if not client:
        print('Could not connect to Weaviate')
        return
    
    try:
        games_collection = client.collections.get('ChessGame')
        
        # Try to get aggregate count first
        try:
            response = games_collection.aggregate.over_all(total_count=True)
            print(f'Total games in ChessGame collection: {response.total_count}')
        except Exception as e:
            print(f'Aggregate method failed: {e}')
            
            # Fallback: fetch objects with limit to estimate
            try:
                response = games_collection.query.fetch_objects(limit=1000)
                count = len(response.objects) if response.objects else 0
                print(f'Games found (up to 1000): {count}')
                if count == 1000:
                    print('Note: There may be more than 1000 games (limit reached)')
            except Exception as e2:
                print(f'Fallback method also failed: {e2}')
                
    except Exception as e:
        print(f'Error accessing ChessGame collection: {e}')
    finally:
        if client:
            # client.close() removed - Weaviate client manages connections automatically

if __name__ == '__main__':
    count_games() 