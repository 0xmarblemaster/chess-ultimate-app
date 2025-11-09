import socketio
import time
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a Socket.IO client
sio = socketio.Client()

# Connection event
@sio.event
def connect():
    logger.info("Connected to server!")
    
    # Test UCI commands
    test_uci_commands()

# Disconnection event
@sio.event
def disconnect():
    logger.info("Disconnected from server")

# Listen for UCI responses
@sio.on('uci_response')
def on_uci_response(data):
    logger.info(f"Received UCI response: {data}")
    
    # Check for analysis_lines in the response
    if 'analysis_lines' in data:
        logger.info(f"Number of analysis lines: {len(data['analysis_lines'])}")
        
        # Print the first analysis line
        if data['analysis_lines']:
            first_line = data['analysis_lines'][0]
            logger.info(f"First line score: {first_line.get('score', 'N/A')}")
            logger.info(f"First line moves: {first_line.get('pv_san', 'N/A')}")

# Listen for UCI errors
@sio.on('uci_error')
def on_uci_error(data):
    logger.error(f"Received UCI error: {data}")

# Listen for connection acknowledgment
@sio.on('connection_ack')
def on_connection_ack(data):
    logger.info(f"Connection acknowledged: {data}")
    
    # Session ID might be in the acknowledgment
    if 'session_id' in data:
        logger.info(f"Session ID: {data['session_id']}")

def test_uci_commands():
    """Test a series of UCI commands"""
    
    # Set the position to the initial position
    sio.emit('uci_command', {
        'command': 'position fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    })
    
    # Wait a bit for the server to process
    time.sleep(1)
    
    # Request analysis
    sio.emit('uci_command', {
        'command': 'go depth 24'
    })
    
    logger.info("UCI commands sent, waiting for responses...")
    
    # Wait for responses
    time.sleep(10)
    
    # Try a new position
    sio.emit('uci_command', {
        'command': 'position fen r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3'
    })
    
    # Wait a bit for the server to process
    time.sleep(1)
    
    # Request analysis
    sio.emit('uci_command', {
        'command': 'go depth 24'
    })
    
    logger.info("Second set of UCI commands sent, waiting for responses...")
    
    # Wait for responses
    time.sleep(10)

if __name__ == "__main__":
    try:
        # Connect to the server
        sio.connect('http://localhost:5001')
        
        # Keep the script running
        sio.wait()
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Disconnect when done
        if sio.connected:
            sio.disconnect() 