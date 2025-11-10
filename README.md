# Ultimate Chess Learning Platform

An AI-powered chess application that combines interactive learning, intelligent AI coaching, and access to 6M+ master games from TWIC, Lichess, and Chess.com archives.

## 🎯 Overview

This project merges two existing chess codebases to create a comprehensive platform with three core features:

1. **Learning Platform** - Built-in curriculum with skill assessment, personalized study plans, and AI tutoring
2. **Analysis Board** - Interactive position analysis with Stockfish WASM engine, AI coaching, and persistent chat sessions
3. **Database Mode** (Phase 2) - Search and explore 6M+ master games with semantic similarity

### Tech Stack

**Frontend:**
- Next.js 16 with App Router
- React 19 + TypeScript 5.9
- Material UI 7.1 + Tailwind CSS 4
- chess.js + react-chessboard
- Stockfish WASM (client-side engine)
- Clerk Authentication
- Mastra AI Framework (agent-based LLM interactions)

**Backend (Phase 1):**
- Flask 3.1.0 (Python 3.9+)
- Supabase (PostgreSQL database)
- LLM Orchestration (API key management, secure routing)
- Anthropic Claude 3.5 Sonnet + OpenAI GPT-4o

**Backend (Phase 2 - Planned):**
- Weaviate (vector database for 6M+ games)
- Redis (conversation cache and session management)

## 🚀 Quick Start

### Prerequisites

- **Node.js** 20.9.0 or higher
- **Python** 3.9 or higher
- **Supabase Account** (free tier available)
- **Clerk Account** (free tier available)
- **Git**
- **Docker** (optional, only needed for Phase 2 services)

### 1. Clone the Repository

```bash
cd /home/marblemaster/Desktop/Cursor/chess-ultimate-app
```

### 2. Set Up Supabase

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Run the database schema from `IMPLEMENTATION_GUIDE.md` (SQL for courses, lessons, user_progress, chat_history)
4. Copy your `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (keep these secure)

### 3. Set Up Clerk Authentication

1. Create a free account at [clerk.com](https://clerk.com)
2. Create a new application
3. Copy your `CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`

### 4. Set Up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env and add:
#   - SUPABASE_URL=your_supabase_url
#   - SUPABASE_SERVICE_KEY=your_service_key
#   - CLERK_SECRET_KEY=your_clerk_secret
#   - ANTHROPIC_API_KEY or OPENAI_API_KEY (for LLM)

# Start Flask server
python app.py
```

Backend will run at `http://localhost:5001`

### 5. Set Up Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file and configure
cp .env.example .env.local
# Edit .env.local and add:
#   - NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_key
#   - CLERK_SECRET_KEY=your_clerk_secret
#   - NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
#   - NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key

# Start development server
npm run dev
```

Frontend will run at `http://localhost:3000`

### 6. Access the Application

Open [http://localhost:3000](http://localhost:3000) in your browser and sign in with Clerk authentication.

## ✨ Key Features

### Multi-Session Chat Management
- **Create Multiple Sessions**: Start new analysis sessions for different games or positions
- **Persistent Storage**: All sessions saved to localStorage - never lose your analysis work
- **Smart Switching**: Seamlessly switch between sessions - board position and chat history load automatically
- **Auto-Generated Titles**: Sessions automatically titled based on chess openings (e.g., "Sicilian Defense", "Queen's Gambit")
- **Session Management**: Rename, delete, and organize your analysis sessions
- **Position Synchronization**: Board FEN and chat messages stay in sync with each session

### Interactive Analysis
- **Stockfish WASM Engine**: Client-side chess engine for real-time position analysis
- **AI Chess Coach**: Get personalized insights and suggestions from Claude AI
- **Opening Database**: Access to master game statistics and opening theory
- **Move Annotations**: Automatic move quality assessment and tactical analysis

## 📖 Documentation

- **[IMPLEMENTATION_GUIDE.md](../../IMPLEMENTATION_GUIDE.md)** - Complete implementation guide for Phase 1
- **[AI_TUTORING_DEEP_COMPARISON.md](../../AI_TUTORING_DEEP_COMPARISON.md)** - Technical comparison of AI approaches
- **[BACKEND_VS_CHESSAGINE_COMPARISON.md](../../BACKEND_VS_CHESSAGINE_COMPARISON.md)** - Architecture comparison

## 🧪 Implementation Phases

### Phase 1: Core Stack (Current Focus)
- ✅ Merged project structure
- ✅ Frontend with Mastra AI framework
- ✅ Stockfish WASM integration (client-side)
- ✅ Persistent chat sessions with localStorage
- ✅ Multi-session management with board position sync
- 🔄 Clerk authentication activation
- 🔄 Supabase database setup
- 🔄 Flask backend for LLM orchestration
- 🔄 Learning platform with progress tracking
- 🔄 AI chat assistant with conversation history

**Phase 1 Deliverables:**
- User authentication and session management
- Learning course system (courses, modules, lessons)
- Progress tracking and lesson unlocking
- AI chat assistant with context retention
- **NEW:** Persistent chat sessions - Create, switch, rename, and delete multiple analysis sessions
- **NEW:** Automatic session title generation based on chess openings and positions
- **NEW:** Board position and chat history saved per session
- Cached LLM responses (24hr TTL)

### Phase 2: Enhanced Features (Planned)
- Redis conversation cache and session management
- Weaviate vector database setup
- TWIC database ingestion (6M+ games)
- Semantic game search by position
- Advanced filtering (player, tournament, ECO)
- Real-time analysis caching

## 🔧 Development

### Running Tests

**Frontend:**
```bash
cd frontend
npm run test
npm run test:coverage
```

**Backend:**
```bash
cd backend
source venv/bin/activate
pytest
pytest --cov=. --cov-report=html
```

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
npm start
```

**Backend:**
```bash
cd backend
# Use production WSGI server (gunicorn, waitress, etc.)
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

## 🌐 Deployment

**Frontend:** Deploy to Vercel (recommended)
```bash
vercel --prod
```

**Backend:** Deploy to Railway, DigitalOcean, or similar
- Ensure Docker services are provisioned
- Set environment variables
- Configure CORS for frontend domain

## 🔐 Authentication

**Phase 1 Status:** Active (Clerk authentication required)

This project uses Clerk for authentication:
- User sign-up/sign-in with email or social providers
- JWT-based session management
- Protected API routes in Flask backend
- User-specific data isolation in Supabase

See [IMPLEMENTATION_GUIDE.md](../../IMPLEMENTATION_GUIDE.md) for complete Clerk setup instructions.

## 📊 Project Structure

```
chess-ultimate-app/
├── frontend/              # Next.js frontend (ChessAgineweb)
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks (useChesster, useEngine)
│   │   ├── server/
│   │   │   └── mastra/    # Mastra AI agents and tools
│   │   ├── stockfish/     # Stockfish WASM integration
│   │   └── theme/         # Material UI theme
│   ├── package.json
│   └── .env.example
├── backend/               # Flask backend (LLM orchestration)
│   ├── api/               # API endpoints
│   │   ├── chat.py        # Chat assistant endpoints
│   │   ├── progress.py    # Learning progress tracking
│   │   └── lessons.py     # Lesson content delivery
│   ├── services/          # Core services
│   │   └── supabase_client.py  # Supabase integration
│   ├── utils/             # Utilities (JWT verification, etc.)
│   ├── app.py             # Flask application entry point
│   ├── requirements.txt
│   └── .env.example
├── data/                  # Data storage (Phase 2)
│   ├── twic/              # TWIC chess games (6M+)
│   ├── lichess/           # Lichess database
│   └── chess_com/         # Chess.com games
├── logs/                  # Application logs
├── docker-compose.yml     # Docker services (Redis, Weaviate - Phase 2)
├── .gitignore
└── README.md
```

## 🤝 Contributing

This project follows the OpenSpec workflow for spec-driven development.

For complex features:
1. Create OpenSpec proposal: `/openspec:proposal`
2. Review and approve specifications
3. Implement: `/openspec:apply`
4. Archive: `/openspec:archive`

See [CLAUDE.md](../CLAUDE.md) for detailed development guidelines.

## 📝 License

See [LICENSE](./frontend/LICENSE) for details.

## 🔗 Resources

- **Supabase:** https://supabase.com
- **Clerk:** https://clerk.com
- **Mastra AI:** https://mastra.ai
- **Next.js:** https://nextjs.org
- **Stockfish WASM:** https://github.com/lichess-org/stockfish.wasm
- **Anthropic:** https://anthropic.com
- **Weaviate:** https://weaviate.io (Phase 2)
- **TWIC:** https://theweekinchess.com/twic (Phase 2)

## 📧 Support

For issues or questions:
- Create an issue in the repository
- Refer to [IMPLEMENTATION_GUIDE.md](../../IMPLEMENTATION_GUIDE.md) for detailed instructions

---

**Status:** Phase 1 Core Stack 🔄 In Progress | Phase 2 Enhanced Features 🔜 Planned
