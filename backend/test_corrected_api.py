#!/usr/bin/env python3
from fixed_twic_loader import get_weaviate_client

print("🧪 Testing corrected API key...")
client = get_weaviate_client()
if client:
    print("🎉 API key works!")
    collection = client.collections.get("ChessGame")
    count = collection.aggregate.over_all(total_count=True).total_count
    print(f"Current database: {count:,} games")
    # client.close() removed - Weaviate client manages connections automatically
else:
    print("❌ Still having API key issues") 