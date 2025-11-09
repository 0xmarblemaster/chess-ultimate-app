from etl.weaviate_loader import get_weaviate_client
import re

client = get_weaviate_client()
collection = client.collections.get('ChessLessonChunk')

# Check for chunks with diagram 1 in the ID
filter_by_id = collection.query.filter.by_property('chunk_id').contains('diagram_doc_img1')
results = collection.query.fetch_objects(limit=5, filters=filter_by_id)
print('Chunks with diagram_doc_img1 in ID:', len(results.objects))
for obj in results.objects:
    print('Chunk ID:', obj.properties.get('chunk_id'))
    print('  Type:', obj.properties.get('type'))
    print('  FEN:', obj.properties.get('fen'))
    print('  Text:', obj.properties.get('text'))

# Test retriever agent pattern
diagram_number = 1
print("\nTesting retriever agent pattern...")
# Try Russian pattern
filter_ru = collection.query.filter.by_property('text').contains(f'диаграмм{diagram_number}')
results_ru = collection.query.fetch_objects(limit=5, filters=filter_ru)
print('Russian pattern results:', len(results_ru.objects))
for obj in results_ru.objects:
    print('Russian pattern match -', 'Type:', obj.properties.get('type'), 'Text:', obj.properties.get('text'))

# Try English pattern
filter_en = collection.query.filter.by_property('text').contains(f'diagram{diagram_number}')
results_en = collection.query.fetch_objects(limit=5, filters=filter_en)
print('English pattern results:', len(results_en.objects))
for obj in results_en.objects:
    print('English pattern match -', 'Type:', obj.properties.get('type'), 'Text:', obj.properties.get('text'))

# Get all chunks
print('\nAll chunks:')
all_chunks = collection.query.fetch_objects(limit=20)
print('Total chunks:', len(all_chunks.objects))
for obj in all_chunks.objects:
    if 'diagram_doc_img1' in obj.properties.get('chunk_id', ''):
        print('\nFound diagram 1:')
        print('  Chunk ID:', obj.properties.get('chunk_id'))
        print('  Type:', obj.properties.get('type'))
        print('  Text:', obj.properties.get('text'))
        print('  FEN:', obj.properties.get('fen'))

# client.close() removed - Weaviate client manages connections automatically 