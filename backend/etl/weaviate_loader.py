import weaviate
import json
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from . import config

def get_weaviate_client() -> Optional[weaviate.Client]:
    """
    Initializes and returns a Weaviate client.
    
    Returns:
        Weaviate client if successful, None otherwise
    """
    if not config.WEAVIATE_ENABLED:
        print("Weaviate is disabled in configuration.")
        return None
    
    headers = {}
    # Add API key for OpenAI if using text2vec-openai
    if config.OPENAI_API_KEY:
        headers["X-OpenAI-Api-Key"] = config.OPENAI_API_KEY

    try:
        # Parse Weaviate URL
        parsed_url = urlparse(config.WEAVIATE_URL)
        host = parsed_url.hostname
        port = parsed_url.port
        http_secure = parsed_url.scheme == "https"

        if host and port:
            # Use Weaviate v3 Client syntax
            client = weaviate.Client(
                url=config.WEAVIATE_URL,
                additional_headers=headers,
                timeout_config=(5, 15)  # (connection_timeout, read_timeout)
            )
        else:
            print(f"Error: Could not parse WEAVIATE_URL: {config.WEAVIATE_URL}")
            return None

        # Check if client is ready using v3 syntax
        try:
            # Simple connectivity test - try to get schema
            schema = client.schema.get()
            if schema:
                print(f"Successfully connected to Weaviate at {config.WEAVIATE_URL}")
                return client
            else:
                print(f"Error: Weaviate instance at {config.WEAVIATE_URL} returned empty schema.")
                return None
        except Exception as e:
            print(f"Error: Weaviate instance at {config.WEAVIATE_URL} is not ready/connected: {e}")
            return None
            
    except Exception as e:
        print(f"Error connecting to Weaviate at {config.WEAVIATE_URL}: {e}")
        return None

def check_collection_exists(client: weaviate.Client, collection_name: str) -> bool:
    """
    Checks if a collection exists in Weaviate.
    
    Args:
        client: Weaviate client
        collection_name: Name of the collection to check
    
    Returns:
        True if collection exists, False otherwise
    """
    try:
        # Use v3 syntax to check if class exists
        schema = client.schema.get()
        if schema and 'classes' in schema:
            class_names = [cls['class'] for cls in schema['classes']]
            return collection_name in class_names
        return False
    except Exception as e:
        print(f"Error checking if collection '{collection_name}' exists: {e}")
        return False

def define_weaviate_schema(client: weaviate.Client) -> bool:
    """
    Defines the ChessLessonChunk schema in Weaviate if it doesn't exist.
    
    Args:
        client: Weaviate client
    
    Returns:
        True if successful, False otherwise
    """
    collection_name = config.WEAVIATE_CLASS_NAME
    
    if check_collection_exists(client, collection_name):
        print(f"Schema (Collection) '{collection_name}' already exists.")
        return True
    
    print(f"Schema (Collection) '{collection_name}' does not exist. Creating...")
    
    try:
        # Define the schema for the collection with simplified properties
        client.collections.create(
            name=collection_name,
            description="A chunk of a chess lesson, potentially including text, FEN, and image references.",
            vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai(),
            properties=[
                weaviate.classes.config.Property(
                    name="chunk_id",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Unique ID for the chunk (e.g., lessonX_taskY)",
                ),
                weaviate.classes.config.Property(
                    name="book_title",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Title of the book/document",
                ),
                weaviate.classes.config.Property(
                    name="lesson_number",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Lesson number or identifier",
                ),
                weaviate.classes.config.Property(
                    name="lesson_title",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Title of the lesson",
                ),
                weaviate.classes.config.Property(
                    name="type",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Type of content in the chunk",
                ),
                weaviate.classes.config.Property(
                    name="language",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Language code (e.g., ru, en)",
                ),
                weaviate.classes.config.Property(
                    name="fen",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="FEN string for the chess position, if any",
                ),
                weaviate.classes.config.Property(
                    name="image",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Filename of the associated image, if any",
                ),
                weaviate.classes.config.Property(
                    name="text",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="The textual content of the chunk",
                ),
                weaviate.classes.config.Property(
                    name="combined_text_for_embedding",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Combined text, FEN, and metadata for embedding",
                ),
            ]
        )
        
        print(f"Successfully created schema for '{collection_name}'")
        return True
    except Exception as e:
        print(f"Error creating schema for '{collection_name}': {e}")
        return False

def prepare_data_for_weaviate(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepares a chunk for insertion into Weaviate.
    
    Args:
        chunk: Dictionary containing chunk data
    
    Returns:
        Dictionary prepared for Weaviate insertion
    """
    # Create a copy to avoid modifying the original
    weaviate_data = chunk.copy()
    
    # Rename id field to avoid conflict with Weaviate's internal id
    if "id" in weaviate_data:
        weaviate_data["chunk_id"] = weaviate_data.pop("id")
    
    # Create a combined field for better semantic search
    combined_text = []
    combined_text.append(f"Book: {weaviate_data.get('book_title', '')}")
    combined_text.append(f"Lesson: {weaviate_data.get('lesson_title', '')}")
    combined_text.append(f"Type: {weaviate_data.get('type', '')}")
    combined_text.append(f"Text: {weaviate_data.get('text', '')}")
    
    if "fen" in weaviate_data:
        combined_text.append(f"FEN: {weaviate_data['fen']}")
    
    weaviate_data["combined_text_for_embedding"] = " ".join(combined_text)
    
    return weaviate_data

def load_chunks_to_weaviate(client: weaviate.Client, chunks: List[Dict[str, Any]]) -> bool:
    """
    Loads chunks into Weaviate.
    
    Args:
        client: Weaviate client
        chunks: List of chunk dictionaries
        
    Returns:
        True if successful, False otherwise
    """
    if not client:
        print("Weaviate client is not initialized.")
        return False
    
    collection_name = config.WEAVIATE_CLASS_NAME
    
    print(f"Loading {len(chunks)} chunks to Weaviate collection '{collection_name}'")
    
    success_count = 0
    error_count = 0
    
    for chunk in chunks:
        try:
            # Prepare data for Weaviate
            weaviate_data = prepare_data_for_weaviate(chunk)
            
            # Use v3 syntax to insert data into Weaviate
            client.data_object.create(
                data_object=weaviate_data,
                class_name=collection_name
            )
            success_count += 1
            
            # Print progress every 10 chunks
            if success_count % 10 == 0:
                print(f"Progress: {success_count}/{len(chunks)} chunks loaded")
                
        except Exception as e:
            print(f"Error loading chunk {chunk.get('id', 'unknown')}: {e}")
            error_count += 1
    
    print(f"Completed loading chunks: {success_count} successful, {error_count} failed")
    return error_count == 0

def search_weaviate(client: weaviate.Client, query_text: str, collection_name: str, top_k: int = 5, fen: Optional[str] = None, properties: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Comprehensive search function for Weaviate.
    
    Args:
        client: Initialized Weaviate client.
        query_text: The text query to search for.
        collection_name: The name of the collection to search.
        top_k: Number of results to return.
        fen: Optional FEN string for chess position-specific searches.
        properties: Optional list of specific properties to return.
    
    Returns:
        A list of search results (dictionaries).
    """
    if not client:
        print("Weaviate client is not initialized for search.")
        return []

    try:
        # If specific properties are requested, use them
        if properties:
            return_properties = properties
        else: # Default properties to return if not specified - FIXED to match actual schema
            if collection_name == "ChessGame":
                # Updated to match actual current schema properties
                return_properties = ["event", "site", "date_utc", "round", "white_player", "black_player", "result",
                                                  "white_elo", "black_elo", "eco", "opening_name", "pgn_moves", 
                                                  "ply_count", "final_fen", "mid_game_fen", "all_ply_fens",
                                                  "source_file", "type"]
            elif collection_name == "ChessLessonChunk":
                # Fixed: Use actual property names from ChessLessonChunk schema
                return_properties = ["language", "content", "image", "type", "processing_method", 
                                                  "source_file", "diagram_analysis", "fen", "book_title", 
                                                  "lesson_number", "lesson_title", "content_type"]
            elif collection_name == "ChessGamesEnhanced":
                # Added support for ChessGamesEnhanced collection
                return_properties = ["white_player", "black_player", "white_elo", "black_elo", "event", 
                                                  "site", "date_utc", "round", "result", "eco", "opening", "pgn_moves",
                                                  "ply_count", "source_file", "searchable_content"]
            else:
                # Generic fallback for other collections
                return_properties = ["fen", "type"]
        
        # Try semantic search first using v3 API
        try:
            response = (client.query
                       .get(collection_name, return_properties)
                       .with_near_text({"concepts": [query_text]})
                       .with_limit(top_k)
                       .with_additional(["distance", "id"])
                       .do())
            
            # Process v3 response format
            if (response and response.get("data") and 
                response["data"].get("Get") and 
                response["data"]["Get"].get(collection_name)):
                
                results = []
                for item in response["data"]["Get"][collection_name]:
                    result = {}
                    # Copy all properties except _additional
                    for prop_name, prop_value in item.items():
                        if prop_name != "_additional":
                            result[prop_name] = prop_value
                    
                    # For ChessGame collection, add UUID fields that users need
                    if collection_name in ["ChessGame", "ChessGamesEnhanced"]:
                        if "_additional" in item and "id" in item["_additional"]:
                            result["game_id"] = item["_additional"]["id"]
                            result["uuid"] = item["_additional"]["id"]
                        result["type"] = "chess_game_search_result"  # Set the type for Answer Agent
                    
                    # Add metadata if available
                    if "_additional" in item:
                        result["_additional"] = {
                            "distance": item["_additional"].get("distance", 0.0),
                            "score": 1.0 - item["_additional"].get("distance", 0.0),
                            "explainScore": "semantic_match"
                        }
                    else:
                        # Provide default metadata when not available
                        result["_additional"] = {
                            "distance": 0.0,
                            "score": 1.0,
                            "explainScore": "semantic_match"
                        }
                    results.append(result)
                
                print(f"Found {len(results)} results for query: '{query_text}' (semantic search)")
                return results
            else:
                print(f"No semantic search results found for '{query_text}'")
                return []
            
        except Exception as semantic_error:
            print(f"Semantic search failed for '{query_text}': {semantic_error}")
            
            # FALLBACK: Use basic fetch for ChessLessonChunk
            if collection_name == "ChessLessonChunk":
                print("Attempting keyword-based fallback for ChessLessonChunk...")
                
                # Extract keywords from query
                query_lower = query_text.lower()
                
                # Look for lesson numbers
                lesson_number = None
                if "урок 2" in query_lower or "lesson 2" in query_lower:
                    lesson_number = "2"
                elif "урок 1" in query_lower or "lesson 1" in query_lower:
                    lesson_number = "1"
                elif "урок 3" in query_lower or "lesson 3" in query_lower:
                    lesson_number = "3"
                
                try:
                    if lesson_number:
                        # Use v3 API to filter by lesson number
                        print(f"Filtering by lesson number: {lesson_number}")
                        response = (client.query
                                   .get(collection_name, return_properties)
                                   .with_where({
                                       "path": ["lesson_number"],
                                       "operator": "Equal",
                                       "valueText": lesson_number
                                   })
                                   .with_limit(top_k * 2)
                                   .with_additional(["id"])
                                   .do())
                        
                        # Process results
                        if (response and response.get("data") and 
                            response["data"].get("Get") and 
                            response["data"]["Get"].get(collection_name)):
                            
                            items = response["data"]["Get"][collection_name]
                            
                            # Further filter by keywords if looking for specific content
                            if "диаграмм" in query_lower or "diagram" in query_lower:
                                # Prioritize items with FEN diagrams
                                fen_results = []
                                other_results = []
                                for item in items:
                                    if item.get('fen'):
                                        fen_results.append(item)
                                    else:
                                        other_results.append(item)
                                filtered_items = fen_results + other_results
                            else:
                                filtered_items = items
                            
                            # Convert to result format
                            results = []
                            for item in filtered_items[:top_k]:
                                result = {}
                                for prop_name, prop_value in item.items():
                                    if prop_name != "_additional":
                                        result[prop_name] = prop_value
                                result["_additional"] = {"distance": 0.0, "score": 1.0, "explainScore": "keyword_match"}
                                results.append(result)
                            
                            print(f"Found {len(results)} results using keyword fallback")
                            return results
                        else:
                            print("No results found with lesson number filter")
                            return []
                    
                    else:
                        # General fallback - just return some lesson content using v3 API
                        print("Using general content fallback...")
                        response = (client.query
                                   .get(collection_name, return_properties)
                                   .with_limit(top_k)
                                   .with_additional(["id"])
                                   .do())
                        
                        if (response and response.get("data") and 
                            response["data"].get("Get") and 
                            response["data"]["Get"].get(collection_name)):
                            
                            results = []
                            for item in response["data"]["Get"][collection_name]:
                                result = {}
                                for prop_name, prop_value in item.items():
                                    if prop_name != "_additional":
                                        result[prop_name] = prop_value
                                result["_additional"] = {"distance": 0.0, "score": 0.5, "explainScore": "general_fallback"}
                                results.append(result)
                            
                            print(f"Found {len(results)} results using general fallback")
                            return results
                        else:
                            return []
                        
                except Exception as fallback_error:
                    print(f"Fallback search also failed: {fallback_error}")
                    return []
            
            else:
                # For other collections, just return empty results
                print(f"No fallback available for collection {collection_name}")
                return []

    except Exception as e:
        print(f"Error during Weaviate search for query '{query_text}': {e}")
        return []

if __name__ == "__main__":
    # Test code for direct execution
    print("Weaviate Loader Module Test")
    print("-------------------------")
    
    client = get_weaviate_client()
    if not client:
        print("Failed to initialize Weaviate client. Exiting.")
        exit(1)
    
    # Check if schema exists and create if needed
    if not check_collection_exists(client, config.WEAVIATE_CLASS_NAME):
        define_weaviate_schema(client)
    
    # Create a test chunk
    test_chunks = [
        {
            "id": "test_chunk_1",
            "book_title": "Test Chess Book",
            "lesson_number": "1",
            "lesson_title": "Introduction to Chess",
            "type": "explanation_group",
            "language": "en",
            "text": "Chess is a strategic board game played between two opponents."
        },
        {
            "id": "test_chunk_2",
            "book_title": "Test Chess Book",
            "lesson_number": "1",
            "lesson_title": "Introduction to Chess",
            "type": "mate_in_1",
            "language": "en",
            "text": "Find the best move that leads to checkmate in one move.",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "image": "test_diagram.png"
        }
    ]
    
    # Load test chunks to Weaviate
    success = load_chunks_to_weaviate(client, test_chunks)
    if success:
        print("Test chunks successfully loaded to Weaviate.")
    else:
        print("Failed to load test chunks to Weaviate.") 