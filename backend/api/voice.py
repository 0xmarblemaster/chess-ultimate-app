from flask import Blueprint, request, jsonify, current_app
import werkzeug.exceptions # For specific exceptions like BadRequest
import os
import tempfile
import requests
import openai
from werkzeug.utils import secure_filename

# Import services with correct module paths
from backend.services.whisper_service import transcribe_audio
from backend.services.elevenlabs_tts import synthesize_speech

# Import orchestrator with correct module path and agents
from backend.etl.agents.orchestrator import run_pipeline
from backend.etl.agents import router_agent_instance, retriever_agent_instance

# To access shared active_games and answer_agent_instance from the main app context
# This can be tricky with Blueprints if not careful. 
# A common way is current_app.config['ANSWER_AGENT_INSTANCE'] or passing it during blueprint registration.
# For active_games, it might be managed by the main app or a shared module.

voice_api_blueprint = Blueprint('voice_api', __name__, url_prefix='/api/voice')

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'm4a', 'webm', 'flac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@voice_api_blueprint.route("/query", methods=['POST'])
def voice_query_route():
    current_app.logger.info("Received request for /api/voice/query")
    
    if 'audio_file' not in request.files:
        current_app.logger.error("No audio_file part in request for voice query")
        return jsonify({"error": "No audio_file part in the request"}), 400

    file = request.files['audio_file']
    session_id = request.form.get('session_id') # Get session_id from form data
    current_app.logger.info(f"Processing voice query for session: {session_id}")

    if file.filename == '':
        current_app.logger.error("No audio file selected for voice query")
        return jsonify({"error": "No audio file selected"}), 400

    if not session_id:
        # Depending on strictness, you might allow queries without session_id (less context for RAG)
        # or require it.
        current_app.logger.warning("Voice query received without session_id.")
        # return jsonify({"error": "session_id is required in form data"}), 400

    audio_bytes = file.read()
    if not audio_bytes:
        current_app.logger.error("Audio file is empty for voice query")
        return jsonify({"error": "Audio file is empty"}), 400

    try:
        # 1. Transcribe Audio to Text
        current_app.logger.info(f"Starting transcription for voice query (session: {session_id})")
        # language can be passed if known, e.g., from user settings
        transcribed_text = transcribe_audio(audio_bytes) #, language="en") 
        current_app.logger.info(f"Whisper transcribed (session: {session_id}): '{transcribed_text}'")

        # 2. Process Text through RAG Pipeline (Orchestrator)
        current_app.logger.info(f"Starting RAG pipeline for voice query: '{transcribed_text}' (session: {session_id})")
        # Import from app.py with correct module path
        # Use the correct answer_agent_instance from etl.agents (not the broken one from app.py)
        from etl.agents import answer_agent_instance as global_answer_agent_instance 
        from backend.app import active_games as global_active_games

        if not global_answer_agent_instance:
            current_app.logger.error("AnswerAgent not available for voice query.")
            return jsonify({"error": "RAG system not initialized (no AnswerAgent)"}), 503

        current_board_fen_for_rag = None
        current_pgn_for_rag = None

        if session_id and session_id in global_active_games:
            # session_lock from app.py would be ideal here if access is concurrent
            # For simplicity now, direct access assuming single-threaded dev or careful management.
            game_state = global_active_games.get(session_id)
            if game_state and 'board' in game_state:
                board = game_state['board']
                current_board_fen_for_rag = board.fen()
                # Simplified PGN generation for voice context (consider reusing app.py logic if complex)
                if board.move_stack:
                    current_pgn_for_rag = " ".join([board.san(m) for m in board.move_stack])
                else:
                    current_pgn_for_rag = "[No moves yet]"
                current_app.logger.info(f"Using FEN: {current_board_fen_for_rag} and PGN: {current_pgn_for_rag} for voice RAG (session: {session_id}).")
            else:
                current_app.logger.warning(f"No board state found for session {session_id} in voice query.")
        else:
            current_app.logger.warning(f"No session_id or session not in active_games for voice query. FEN/PGN context will be missing.")

        current_app.logger.info(f"Calling orchestrator for voice query (session: {session_id})")
        # Call the orchestrator's run_pipeline function with all required parameters
        pipeline_state = run_pipeline(
            initial_query=transcribed_text,
            router_agent_instance=router_agent_instance,
            retriever_agent_instance=retriever_agent_instance,
            answer_agent_instance=global_answer_agent_instance,
            current_board_fen=current_board_fen_for_rag,
            session_pgn=current_pgn_for_rag,
            session_id=session_id  # Pass session_id for conversation memory
        )
        current_app.logger.info(f"Orchestrator pipeline completed for voice query (session: {session_id})")

        rag_answer = pipeline_state.get("final_answer")
        if pipeline_state.get("error_message") and not rag_answer:
             # If pipeline had an error and no answer, return that error
            current_app.logger.error(f"RAG pipeline error for voice query (session: {session_id}): {pipeline_state.get('error_message')}")
            return jsonify({"error": pipeline_state.get("error_message"), "transcribed_text": transcribed_text}), 500
        
        if not rag_answer:
            current_app.logger.warning(f"RAG pipeline returned no answer for (session: {session_id}): '{transcribed_text}'")
            rag_answer = "I received your query, but I couldn't find a specific answer right now." # Default response

        current_app.logger.info(f"RAG answer for voice (session: {session_id}): '{rag_answer[:100]}...'")

        # 3. Synthesize Speech from RAG Answer
        current_app.logger.info(f"Starting ElevenLabs TTS for voice response (session: {session_id})")
        audio_data_uri = synthesize_speech(rag_answer)
        current_app.logger.info(f"ElevenLabs TTS synthesized for voice (session: {session_id}).")

        current_app.logger.info(f"Voice query complete, returning response for session: {session_id}")
        return jsonify({
            "text_request": transcribed_text,
            "text_response": rag_answer,
            "audio_response_uri": audio_data_uri,
            "query_type": pipeline_state.get("query_type"),
            "metadata": pipeline_state.get("router_metadata"),
            "retrieved_chunks_count": len(pipeline_state.get("retrieved_chunks", []))
        }), 200

    except werkzeug.exceptions.BadRequest as e: # Catch specific Flask/Werkzeug errors
        current_app.logger.error(f"BadRequest in voice query (session: {session_id}): {e}")
        return jsonify({"error": str(e)}), 400
    except ValueError as e:
        # Catches errors from our services like API key not set or empty audio
        current_app.logger.error(f"ValueError in voice query processing (session: {session_id}): {e}")
        return jsonify({"error": str(e)}), 400 
    except openai.APIError as e:
        current_app.logger.error(f"OpenAI API error during voice query (session: {session_id}): {e}")
        return jsonify({"error": f"STT service error: {str(e)}"}), 502 # Bad Gateway for upstream errors
    except requests.exceptions.HTTPError as e:
        # Specifically for ElevenLabs HTTP errors if synthesize_speech raises it
        current_app.logger.error(f"ElevenLabs API HTTP error (session: {session_id}): {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"TTS service error: {e.response.status_code} - {e.response.text}"}), 502
    except Exception as e:
        current_app.logger.error(f"Unexpected error in voice query (session: {session_id}): {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# New STT-only endpoint
@voice_api_blueprint.route('/stt', methods=['POST'])
def stt_only_endpoint():
    current_app.logger.info("Received request for /api/voice/stt")
    if 'audio_file' not in request.files:
        current_app.logger.error("No audio_file part in request for STT")
        return jsonify({"error": "No audio_file part in the request"}), 400

    file = request.files['audio_file']
    session_id = request.form.get('session_id', 'default_stt_session') # Use a default if not provided

    if file.filename == '':
        current_app.logger.error("No selected audio file for STT")
        return jsonify({"error": "No audio file selected"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        temp_audio_file_path = None
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            temp_audio_file_path = os.path.join(temp_dir, filename)
            file.save(temp_audio_file_path)
            current_app.logger.info(f"Audio file for STT saved temporarily to: {temp_audio_file_path} (session: {session_id})")

            with open(temp_audio_file_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                transcribed_text = transcribe_audio(audio_bytes)
            
            if transcribed_text is None: # Whisper service might return None on error
                current_app.logger.error(f"Whisper transcription returned None for STT (session: {session_id})")
                return jsonify({"error": "Failed to transcribe audio"}), 500
            
            current_app.logger.info(f"STT successful (session: {session_id}): '{transcribed_text}'")
            return jsonify({"transcribed_text": transcribed_text}), 200

        except Exception as e:
            current_app.logger.error(f"Error in STT-only endpoint (session: {session_id}): {e}", exc_info=True)
            return jsonify({"error": "An internal error occurred during speech-to-text processing."}), 500
        finally:
            if temp_audio_file_path and os.path.exists(temp_audio_file_path):
                try:
                    os.remove(temp_audio_file_path)
                    if temp_dir and os.path.exists(temp_dir) and not os.listdir(temp_dir): # Check if dir is empty
                        os.rmdir(temp_dir)
                except OSError as e:
                    current_app.logger.error(f"Error removing temporary STT audio file/dir {temp_audio_file_path}: {e}")
    else:
        current_app.logger.error(f"Invalid file type for STT: {file.filename}")
        return jsonify({"error": "Invalid file type"}), 400


# This route would serve the TTS audio files generated by elevenlabs_tts service
# It assumes that elevenlabs_tts.convert_text_to_speech_local saves files to a known directory
# that can be mapped here. For example, 'elevenlabs_output' in the instance path or static folder.
@voice_api_blueprint.route('/audio/<filename>', methods=['GET'])
def serve_tts_audio(filename):
    # IMPORTANT: This is a simplified way to serve files.
    # In production, use a more secure and robust method.
    # Ensure the directory is correctly configured and secured.
    # Example: current_app.config['TTS_OUTPUT_FOLDER']
    tts_output_directory = os.path.join(current_app.instance_path, 'elevenlabs_output') 
    # Create directory if it doesn't exist, though files should already be there.
    os.makedirs(tts_output_directory, exist_ok=True) 
    
    current_app.logger.info(f"Attempting to serve TTS audio file: {filename} from {tts_output_directory}")
    try:
        # flask.send_from_directory is safer for serving files
        from flask import send_from_directory
        return send_from_directory(tts_output_directory, filename, as_attachment=False)
    except FileNotFoundError:
        current_app.logger.error(f"TTS audio file not found: {filename} in {tts_output_directory}")
        return jsonify({"error": "Audio file not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error serving TTS audio file {filename}: {e}", exc_info=True)
        return jsonify({"error": "Could not serve audio file"}), 500

# To make this blueprint usable, it needs to be registered in your main app.py:
# from .api.voice import voice_api_blueprint
# app.register_blueprint(voice_api_blueprint)
# 
# And ensure OPENAI_API_KEY and ELEVEN_API_KEY (and optionally ELEVEN_VOICE_ID)
# are loaded from .env in app.py or set in the environment. 