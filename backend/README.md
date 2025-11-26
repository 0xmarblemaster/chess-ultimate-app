# Chess Companion Backend

This is the backend service for the Chess Companion application, providing chess analysis, question answering, and voice interaction capabilities.

## Architecture

The backend is built with a modular service-oriented architecture:

```
backend/
├── api/                # API routes and endpoints
├── services/           # Service modules for business logic
│   ├── stockfish_engine.py       # Chess engine service
│   ├── fen_converter_service.py  # FEN notation conversion
│   ├── whisper_service.py        # Speech-to-text service
│   ├── elevenlabs_tts.py         # Text-to-speech service
│   ├── chunking_service.py       # Document chunking
│   └── vector_store_service.py   # Vector database interface
├── database/           # Data storage interfaces
├── agents/             # LLM agents for different tasks
├── etl/                # Data extraction, transformation, loading
├── utils/              # Shared utilities
├── app.py              # Main application entry point
└── config.py           # Configuration management
```

## Getting Started

### Prerequisites

- Python 3.9+
- Stockfish chess engine installed locally
- Weaviate vector database (local or remote)
- OpenAI API key for GPT models
- ElevenLabs API key for voice synthesis (optional)

### Installation

1. Clone the repository
2. Set up a Python virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
STOCKFISH_PATH=/path/to/stockfish
WEAVIATE_URL=http://localhost:8080
```

5. Start the server:
```bash
python app.py
```

## Key Components

### Services

Services are specialized modules providing specific functionality:

- **StockfishEngine**: Interface to the Stockfish chess engine for move analysis
- **FENConverterService**: Conversion between chess board images and FEN notation
- **WhisperService**: Speech-to-text conversion
- **ElevenLabsTTS**: Text-to-speech synthesis
- **ChunkingService**: Document chunking for RAG applications
- **VectorStoreService**: Interface to the Weaviate vector database

## Stockfish Integration

The application integrates the Stockfish chess engine for providing position analysis. This section details how Stockfish works within the system.

### Overview

The Stockfish integration is architected with multiple access methods:

1. **HTTP API Endpoint**: For stateless position analysis
2. **WebSocket Interface**: For interactive UCI command communication
3. **Service Layer**: Encapsulating Stockfish functionality for internal use

The recommended approach for frontend integration is using the HTTP API endpoint, which provides the most reliable and consistent results.

### Configuration

Stockfish requires proper configuration in the `.env` file:

```
STOCKFISH_PATH=/path/to/stockfish
```

If not specified, the system will attempt to find Stockfish in the system PATH.

### HTTP API

The primary way to access Stockfish analysis is through the `/api/chess/analyze_position` endpoint:

```
POST /api/chess/analyze_position
Content-Type: application/json

{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
}
```

Response format:

```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "commentary": "Stockfish analysis: Best line eval=+0.34",
  "is_critical": false,
  "lines": [
    {
      "line_number": 1,
      "score": 0.34,
      "evaluation_numerical": 0.34,
      "evaluation_string": "+0.34",
      "mate_in": null,
      "depth": 24,
      "pv_san": "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e6 Bf4 d6",
      "bestmove": "e4"
    },
    // Additional analysis lines...
  ]
}
```

Key fields in each analysis line:
- `line_number`: The rank of this variation (1 = best line)
- `score`: Numerical evaluation in pawns (positive = white advantage)
- `evaluation_string`: Human-readable evaluation string
- `mate_in`: Number of moves to mate (null if not a mate sequence)
- `depth`: Depth of analysis
- `pv_san`: The principal variation in Standard Algebraic Notation
- `bestmove`: The recommended first move of this line

### WebSocket Interface

For specialized use cases, a WebSocket interface is available using Socket.IO:

```javascript
// Connect to socket
const socket = io('http://localhost:5001');

// Send UCI commands
socket.emit('uci_command', { 
  command: 'position fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
});
socket.emit('uci_command', { command: 'go depth 24' });

// Listen for responses
socket.on('uci_response', (data) => {
  console.log('Analysis results:', data.analysis_lines);
});

// Handle errors
socket.on('uci_error', (error) => {
  console.error('UCI error:', error);
});
```

Note: The WebSocket interface may be less stable with certain versions of python-chess, particularly with the `Score()` method. Use the HTTP API when possible.

### Internal Service Usage

For internal use by other components, use the `analyze_fen_with_stockfish_service` function from `stockfish_analyzer.py`:

```python
from stockfish_analyzer import analyze_fen_with_stockfish_service

analysis_lines = analyze_fen_with_stockfish_service(
    fen_string="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    time_limit=5.0,  # 5 second timeout
    depth_limit=24,  # Maximum depth
    multipv=3        # Number of principal variations
)
```

### Frontend Integration

The frontend should use the HTTP API for analysis. Here's a recommended example in React/TypeScript:

```typescript
async function analyzePosition(fen: string) {
  try {
    const response = await fetch('http://localhost:5001/api/chess/analyze_position', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ fen }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    // Process the analysis lines
    const frontendLines = data.lines.map((line) => ({
      score: line.evaluation_numerical,
      mate: line.mate_in,
      line: line.pv_san || ''
    }));
    
    // Update UI with analysis results
    // ...
  } catch (error) {
    console.error('Analysis error:', error);
  }
}
```

### ETL Pipeline

The ETL pipeline processes chess documents:

1. **Extract**: Read PGN files, books, etc.
2. **Transform**: Convert content into chunks with FEN conversion
3. **Load**: Store processed chunks in Weaviate

### Configuration

The application uses a central configuration system in `config.py` with environment-based defaults.

## Testing

Run the test suite:

```bash
pytest
```

Or test a specific component:

```bash
pytest tests/services/test_stockfish_engine.py
```

## API Documentation

API endpoints are available at http://localhost:5000/api/docs when the server is running.

## License

This project is licensed under the MIT License.