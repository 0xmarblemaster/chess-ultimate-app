import socketio
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('stockfish_test')

class StockfishClient:
    def __init__(self):
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.connected = False
        
        @self.sio.event
        def connect():
            logger.info('Connected to server')
            self.connected = True
            
        @self.sio.event
        def disconnect():
            logger.info('Disconnected from server')
            self.connected = False
        
        # Listen to all events
        @self.sio.on('*')
        def catch_all(event, data):
            logger.debug(f'Received event: {event}, data: {data}')
            
        @self.sio.on('uci_response')
        def on_uci_response(data):
            logger.info(f'Received UCI response: {data}')
            
        @self.sio.on('uci_error')
        def on_uci_error(data):
            logger.error(f'Received UCI error: {data}')

        @self.sio.on('fen_updated')
        def on_fen_updated(data):
            logger.info(f'FEN updated: {data}')
    
    def connect_to_server(self, url='http://localhost:5001'):
        try:
            self.sio.connect(url)
            logger.info(f'Connected to server with session ID: {self.sio.sid}')
            return True
        except Exception as e:
            logger.error(f'Failed to connect to server: {e}')
            return False
    
    def initialize_game(self, fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        """Initialize the game state for the session using the update_backend_fen event"""
        if not self.connected:
            logger.error('Not connected to server')
            return
        
        # First connect event to force session creation in active_games
        self.sio.emit('connect', {})
        time.sleep(0.5)
        
        # Then update the FEN
        self.sio.emit('update_backend_fen', {
            'fen': fen
        })
        logger.info(f'Initialized game state with FEN: {fen}')
        time.sleep(1)  # Give server time to initialize
    
    def send_position(self, fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        if not self.connected:
            logger.error('Not connected to server')
            return
        
        self.sio.emit('uci_command', {
            'command': f'position fen {fen}'
        })
        logger.info(f'Sent position command with FEN: {fen}')
    
    def send_go(self, depth=10):
        if not self.connected:
            logger.error('Not connected to server')
            return
        
        self.sio.emit('uci_command', {
            'command': f'go depth {depth}'
        })
        logger.info(f'Sent go command with depth: {depth}')
    
    def disconnect_from_server(self):
        if self.connected:
            self.sio.disconnect()
            logger.info('Disconnected from server')

if __name__ == '__main__':
    client = StockfishClient()
    
    if client.connect_to_server():
        # Wait a bit for initialization
        time.sleep(1)
        
        # Initialize game state first
        client.initialize_game()
        
        # Send position and go commands
        client.send_position()
        time.sleep(1)
        client.send_go(depth=10)
        
        # Wait for response
        logger.info('Waiting for response...')
        time.sleep(10)
        
        # Disconnect
        client.disconnect_from_server()
    else:
        logger.error('Test failed: Could not connect to server') 