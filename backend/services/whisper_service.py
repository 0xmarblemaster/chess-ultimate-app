import openai
import tempfile
import os

# Whisper uses the globally configured openai.api_key and openai.api_base
# Ensure OPENAI_API_KEY (or DEEPSEEK_API_KEY if using a proxy/alternative) 
# is loaded via load_dotenv() in your main app.py or set in the environment.

def transcribe_audio(audio_bytes: bytes, language: str = None) -> str:
    """
    Transcribes audio using OpenAI Whisper API.

    Args:
        audio_bytes: The audio data in bytes.
        language: Optional. The language of the audio in ISO-639-1 format (e.g., 'en', 'es').
                  If None, Whisper will attempt to auto-detect the language.

    Returns:
        The transcribed text.

    Raises:
        openai.APIError: If the OpenAI API call fails.
        ValueError: If audio_bytes is empty.
    """
    if not audio_bytes:
        raise ValueError("Audio bytes cannot be empty.")

    # Whisper expects a file-like object. We use a temporary file.
    # Ensure the temporary file is opened in binary write mode ('wb')
    # and that it has a name attribute, which NamedTemporaryFile provides.
    # The suffix helps Whisper determine the file type, common types are .mp3, .wav, .ogg, .m4a etc.
    # Using .mp3 as a common intermediate format if the original is unknown, but be mindful of conversions.
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
        temp_file.write(audio_bytes)
        temp_file.flush() # Ensure all data is written to disk before Whisper reads it
        
        # Get the file name for the API call
        file_path = temp_file.name

        try:
            # The `openai.Audio.transcribe` method expects the file path as a string
            # or a file object opened in binary read mode (`rb`).
            # Since we just wrote to temp_file, we can pass its name.
            # To pass the file object directly, we would need to re-open it in 'rb' mode after writing,
            # or pass temp_file.file (the underlying file object) IF the API supports it, but path is safer.
            
            # Re-open the temp file in binary read mode for transcription
            with open(file_path, "rb") as audio_file_for_transcription:
                if language:
                    response = openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file_for_transcription,
                        language=language
                    )
                else:
                    response = openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file_for_transcription
                    )
        except openai.APIError as e:
            print(f"OpenAI Whisper API Error: {e}")
            raise # Re-raise the specific OpenAI APIError
        except Exception as e:
            # Catch other potential errors during file operations or API call
            print(f"An unexpected error occurred during transcription: {e}")
            raise openai.APIError(f"Transcription failed due to an unexpected error: {e}") # Wrap in APIError for consistency

    return response.text # The new SDK uses .text attribute

if __name__ == '__main__':
    # Example Usage:
    # This requires an audio file named 'test_audio.mp3' in the same directory as this script,
    # and your OpenAI API key to be set in the environment (e.g., via a .env file loaded by your main app).

    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        from dotenv import load_dotenv
        print(f"Loading .env file from: {dotenv_path} for Whisper test")
        load_dotenv(dotenv_path=dotenv_path)
        # Initialize OpenAI client credentials if necessary (usually done globally)
        # For Whisper, openai.api_key needs to be set.
        # If your app.py initializes openai.OpenAI(api_key=..., base_url=...),
        # that sets the global key if base_url is for OpenAI or a compatible service.
        # If deepseek is used, ensure it can handle /audio/transcriptions endpoint or use openai key directly for whisper.
        
        # Attempt to set API key for standalone test if not already configured by a global client
        if not openai.api_key:
             openai_api_key = os.getenv("OPENAI_API_KEY")
             deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") # Example, if deepseek is primary

             if openai_api_key:
                 openai.api_key = openai_api_key
                 print("Using OPENAI_API_KEY for Whisper test.")
             elif deepseek_api_key and os.getenv("USE_DEEPSEEK_FOR_WHISPER", "false").lower() == "true":
                 # This branch is less likely for Whisper unless Deepseek provides a compatible audio API endpoint
                 openai.api_key = deepseek_api_key
                 openai.api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1") # Ensure this is correct for audio
                 print(f"Attempting to use DEEPSEEK_API_KEY and base URL {openai.api_base} for Whisper test.")
             else:
                 print("Neither OPENAI_API_KEY found nor Deepseek configured for Whisper test. Transcription will likely fail.")

    else:
        print(f".env file not found at {dotenv_path}. Ensure API keys are set in environment.")

    if not openai.api_key:
        print("OpenAI API key is not set. Please set OPENAI_API_KEY. Cannot run Whisper example.")
    else:
        # Create a dummy audio file for testing if one doesn't exist
        # For a real test, replace with an actual audio file path.
        dummy_audio_file_path = "test_audio.mp3" 
        # You would typically have a real audio file, e.g., from a user upload.
        # For this example, let's assume one exists or skip if not.

        if not os.path.exists(dummy_audio_file_path):
            print(f"Test audio file '{dummy_audio_file_path}' not found. Skipping transcription example.")
            # You could create a tiny silent mp3 here for a basic API call test, but it's complex.
            # Example: from pydub import AudioSegment
            # silence = AudioSegment.silent(duration=1000) # 1 second of silence
            # silence.export(dummy_audio_file_path, format="mp3")
            # print(f"Created dummy '{dummy_audio_file_path}' for testing.")
        else:
            print(f"Attempting to transcribe '{dummy_audio_file_path}'")
            try:
                with open(dummy_audio_file_path, "rb") as audio_file:
                    audio_bytes_content = audio_file.read()
                
                if not audio_bytes_content:
                    print("Test audio file is empty.")
                else:
                    transcribed_text = transcribe_audio(audio_bytes_content, language="en") # Specify language e.g., "en"
                    print(f"Transcribed Text: {transcribed_text}")
            except FileNotFoundError:
                print(f"Test audio file '{dummy_audio_file_path}' not found.")
            except ValueError as ve:
                print(f"ValueError during transcription: {ve}")
            except openai.APIError as apie:
                print(f"OpenAI API Error during transcription: {apie}")
            except Exception as e:
                print(f"An unexpected error occurred during transcription test: {e}") 