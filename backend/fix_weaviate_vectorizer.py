#!/usr/bin/env python3
from etl.weaviate_loader import get_weaviate_client
from etl import config
import weaviate

def fix_weaviate_schema():
    """
    Fix the Weaviate schema by recreating it with proper vectorizer configuration
    """
    print("Connecting to Weaviate...")
    client = get_weaviate_client()
    if not client:
        print("Error: Could not connect to Weaviate")
        return
    
    collection_name = config.WEAVIATE_CLASS_NAME
    
    try:
        # Check if collection exists
        print(f"Checking if collection '{collection_name}' exists...")
        if client.collections.exists(collection_name):
            print(f"Deleting existing collection '{collection_name}'...")
            client.collections.delete(collection_name)
            print(f"Collection '{collection_name}' deleted successfully.")
        
        print(f"Creating collection '{collection_name}' with proper vectorizer configuration...")
        
        # Create the collection with proper configuration
        client.collections.create(
            name=collection_name,
            description="A chunk of a chess lesson, potentially including text, FEN, and image references.",
            vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai(),
            properties=[
                weaviate.classes.config.Property(
                    name="chunk_id",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Unique ID for the chunk (e.g., lessonX_taskY)",
                    tokenization=weaviate.classes.config.Property.Tokenization.FIELD,
                ),
                weaviate.classes.config.Property(
                    name="book_title",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Title of the book/document",
                    tokenization=weaviate.classes.config.Property.Tokenization.WORD,
                ),
                weaviate.classes.config.Property(
                    name="lesson_number",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Lesson number or identifier",
                    tokenization=weaviate.classes.config.Property.Tokenization.FIELD,
                ),
                weaviate.classes.config.Property(
                    name="lesson_title",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Title of the lesson",
                    tokenization=weaviate.classes.config.Property.Tokenization.WORD,
                ),
                weaviate.classes.config.Property(
                    name="type",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Type of content in the chunk",
                    tokenization=weaviate.classes.config.Property.Tokenization.FIELD,
                ),
                weaviate.classes.config.Property(
                    name="language",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Language code (e.g., ru, en)",
                    tokenization=weaviate.classes.config.Property.Tokenization.FIELD,
                ),
                weaviate.classes.config.Property(
                    name="fen",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="FEN string for the chess position, if any",
                    tokenization=weaviate.classes.config.Property.Tokenization.FIELD,
                    indexing=weaviate.classes.config.Property.Indexing(
                        filterable=True,
                        searchable=True,
                    ),
                ),
                weaviate.classes.config.Property(
                    name="image",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Filename of the associated image, if any",
                    tokenization=weaviate.classes.config.Property.Tokenization.FIELD,
                ),
                weaviate.classes.config.Property(
                    name="text",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="The textual content of the chunk",
                    skip_vectorization=False,
                ),
                weaviate.classes.config.Property(
                    name="combined_text_for_embedding",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Combined text, FEN, and metadata for embedding",
                    indexing=weaviate.classes.config.Property.Indexing(
                        filterable=False,
                        searchable=False,
                    ),
                    skip_vectorization=False,
                ),
            ]
        )
        
        print(f"Collection '{collection_name}' created successfully with proper vectorizer configuration.")
        print("Now you'll need to run the ETL pipeline again to reload the data.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # client.close() removed - Weaviate client manages connections automatically

if __name__ == "__main__":
    fix_weaviate_schema() 