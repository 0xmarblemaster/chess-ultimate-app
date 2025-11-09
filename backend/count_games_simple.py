#!/usr/bin/env python3

import weaviate
import os

def count_games_simple():
    """Count games using HTTP-only connection to avoid gRPC issues."""
    
    # Set up headers for OpenAI API key
    headers = {}
    openai_key = "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"
    if openai_key:
        headers["X-OpenAI-Api-Key"] = openai_key
    
    try:
        # Connect using HTTP only to avoid gRPC issues
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            headers=headers,
            skip_init_checks=True  # Skip gRPC health checks
        )
        
        print("Connected to Weaviate successfully")
        
        # Get the ChessGame collection
        games_collection = client.collections.get('ChessGame')
        
        # Try aggregate count first
        try:
            response = games_collection.aggregate.over_all(total_count=True)
            total_count = response.total_count
            print(f'Total games in ChessGame collection: {total_count}')
            return total_count
        except Exception as e:
            print(f'Aggregate method failed: {e}')
            
            # Fallback: fetch objects to count
            try:
                response = games_collection.query.fetch_objects(limit=10000)
                count = len(response.objects) if response.objects else 0
                print(f'Games found (up to 10,000): {count}')
                if count == 10000:
                    print('Note: There may be more than 10,000 games (limit reached)')
                return count
            except Exception as e2:
                print(f'Fallback method also failed: {e2}')
                return 0
                
    except Exception as e:
        print(f'Error connecting to Weaviate: {e}')
        return 0
    finally:
        try:
            # client.close() removed - Weaviate client manages connections automatically
        except:
            pass

if __name__ == '__main__':
    count_games_simple() 