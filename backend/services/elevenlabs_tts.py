import requests
import os
import base64

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
# ELEVEN_VOICE_ID is fetched within the function to allow dynamic changes via .env
# Default is "Rachel" if not set.

def synthesize_speech(text: str) -> str:
    """
    Synthesizes speech from text using ElevenLabs API and returns a base64 encoded audio data URI.
    """
    if not ELEVEN_API_KEY:
        # It's better to raise an error or log if the key is critical
        print("ERROR: ELEVEN_API_KEY environment variable not set.")
        raise ValueError("ELEVEN_API_KEY environment variable not set.")
    
    voice_id_to_use = os.getenv("ELEVEN_VOICE_ID", "Rachel") # Default to Rachel

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id_to_use}"
    
    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",  # or eleven_multilingual_v2
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    try:
        response.raise_for_status() 
    except requests.exceptions.HTTPError as e:
        print(f"ElevenLabs API Error: {e}")
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        raise # Re-raise the exception
        
    audio_base64 = base64.b64encode(response.content).decode('utf-8')
    return f"data:audio/mpeg;base64,{audio_base64}"

if __name__ == '__main__':
    # This example requires ELEVEN_API_KEY and optionally ELEVEN_VOICE_ID 
    # to be set in your environment or .env file.
    # Ensure your .env file is in the root of the project (mvp1/)
    # or adjust the dotenv_path accordingly.
    
    # Correct path assuming .env is in mvp1/
    # and this script is run from mvp1/backend/services/
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    
    # Check if .env exists at the expected path
    if os.path.exists(dotenv_path):
        from dotenv import load_dotenv
        print(f"Loading .env file from: {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path)
    else:
        print(f".env file not found at {dotenv_path}. Please ensure it exists or environment variables are set manually.")

    # Re-fetch ELEVEN_API_KEY after attempting to load .env
    ELEVEN_API_KEY_TEST = os.getenv("ELEVEN_API_KEY")
    ELEVEN_VOICE_ID_TEST = os.getenv("ELEVEN_VOICE_ID")

    if not ELEVEN_API_KEY_TEST:
        print("ELEVEN_API_KEY is not set. Please set it in your .env file or environment. Cannot run example.")
    else:
        print(f"Using ElevenLabs API Key: {'*' * (len(ELEVEN_API_KEY_TEST) - 4) + ELEVEN_API_KEY_TEST[-4:] if ELEVEN_API_KEY_TEST else 'Not Set'}")
        print(f"Using ElevenLabs Voice ID: {ELEVEN_VOICE_ID_TEST or 'Rachel (default)'}")
        try:
            sample_text = "Hello, this is a test of the ElevenLabs text to speech service."
            print(f"Attempting to synthesize: '{sample_text}'")
            audio_data_uri = synthesize_speech(sample_text)
            print(f"Successfully synthesized speech.")
            print(f"Audio Data URI (first 100 chars): {audio_data_uri[:100]}...")
            
            # Example of how to save the audio locally for verification
            # import base64
            # # Make sure the 'output' directory exists or choose a different path
            # output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'output') 
            # os.makedirs(output_dir, exist_ok=True)
            # output_path = os.path.join(output_dir, "test_speech_elevenlabs.mp3")

            # if audio_data_uri.startswith("data:audio/mpeg;base64,"):
            #     header, encoded = audio_data_uri.split(",", 1)
            #     data = base64.b64decode(encoded)
            #     with open(output_path, "wb") as f:
            #         f.write(data)
            #     print(f"Saved test speech to {output_path}")
            # else:
            #     print("Could not decode audio data URI, prefix missing.")

        except ValueError as ve:
            print(f"ValueError: {ve}")
        except requests.exceptions.HTTPError as he:
            # This will now print more detailed info from the synthesize_speech function
            print(f"HTTPError during synthesis example: {he}")
        except Exception as e:
            print(f"An unexpected error occurred in example usage: {e}") 