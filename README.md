# Ultimate Chess Learning Platform

An AI-powered chess application that combines interactive learning, advanced position analysis, and access to 6M+ master games from TWIC, Lichess, and Chess.com archives.

## 🎯 Overview

This project merges two existing chess codebases to create a comprehensive platform with three core features:

1. **Learning Platform** - Built-in curriculum with skill assessment, personalized study plans, and AI tutoring
2. **Analysis Board** - Interactive position analysis with Stockfish engine and AI coaching
3. **Database Mode** - Search and explore 6M+ master games with semantic similarity

### Tech Stack

**Frontend:**
- Next.js 16 with App Router
- React 19 + TypeScript 5.9
- Material UI 7.1 + Tailwind CSS 4
- chess.js + react-chessboard
- Stockfish WASM (client-side engine)
- Clerk Authentication

**Backend:**
- Flask 3.1.0 (Python 3.9+)
- Weaviate (vector database)
- Redis (conversation cache)
- SQLite (conversation persistence)
- Stockfish (native binary)
- Anthropic Claude 3.5 Sonnet + OpenAI GPT-4o

## 🚀 Quick Start

### Prerequisites

- **Node.js** 20.9.0 or higher
- **Python** 3.9 or higher
- **Docker** and **Docker Compose** (for services)
- **Git**

### 1. Clone the Repository

```bash
cd /home/marblemaster/Desktop/Cursor/chess-ultimate-app
```

### 2. Start Backend Services

Start Redis and Weaviate using Docker Compose:

```bash
docker-compose up -d
```

Verify services are running:

```bash
docker-compose ps
```

You should see `chess-redis` and `chess-weaviate` with status "Up".

### 3. Set Up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env and add your API keys (see SETUP.md for details)

# Start Flask server
python app.py
```

Backend will run at `http://localhost:5001`

### 4. Set Up Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file and configure
cp .env.example .env.local
# Edit .env.local and add API keys if needed

# Start development server
npm run dev
```

Frontend will run at `http://localhost:3000`

### 5. Access the Application

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📖 Documentation

- **[SETUP.md](./SETUP.md)** - Detailed setup instructions including API keys and Clerk authentication
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture and design decisions

## 🧪 Features

### Phase 1: Foundation (Current)
- ✅ Merged project structure
- ✅ Docker Compose for services
- ✅ Environment configuration
- ✅ Basic documentation

### Phase 2: Authentication (Planned)
- Enable Clerk authentication
- User session management
- Clerk JWT verification in backend
- Protected routes and API endpoints

### Phase 3: Conversation Memory (Planned)
- Integrate Redis conversation cache
- SQLite persistence for chat history
- Multi-turn context retention
- User-specific conversation threads

### Phase 4: Database Mode (Planned)
- TWIC database download and ingestion (6M+ games)
- Weaviate vector search implementation
- Position-based game search
- Player/tournament/ECO filtering

### Phase 5: Learning Platform (Planned)
- Skill assessment system
- Personalized study plans
- Interactive lessons with diagrams
- Progress tracking and analytics

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

**Current Status:** Disabled (local development mode)

This project has Clerk authentication fully integrated but commented out for easier initial setup.

To enable authentication:
1. Create a Clerk account at [clerk.com](https://clerk.com)
2. Add Clerk API keys to `.env` files (see [SETUP.md](./SETUP.md))
3. Uncomment Clerk code in `frontend/src/app/layout.tsx`
4. Restart frontend development server

Authentication will be enabled in Phase 2 of the project.

## 📊 Project Structure

```
chess-ultimate-app/
├── frontend/              # Next.js frontend (ChessAgineweb)
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks (useChesster, useEngine)
│   │   ├── stockfish/     # Stockfish WASM integration
│   │   └── theme/         # Material UI theme
│   ├── package.json
│   └── .env.example
├── backend/               # Flask backend (MVP1)
│   ├── api/               # API endpoints
│   ├── etl/               # ETL pipeline and agents
│   │   └── agents/        # RAG agents (router, retriever, answer, game search)
│   ├── services/          # Core services (Stockfish, Whisper, ElevenLabs, Vector DB)
│   ├── utils/             # Utilities
│   ├── app.py             # Flask application entry point
│   ├── requirements.txt
│   └── .env.example
├── data/                  # Data storage
│   ├── twic/              # TWIC chess games
│   ├── lichess/           # Lichess database
│   └── chess_com/         # Chess.com games
├── logs/                  # Application logs
├── docker-compose.yml     # Docker services (Redis, Weaviate)
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

- **Stockfish:** https://stockfishchess.org
- **Weaviate:** https://weaviate.io
- **Next.js:** https://nextjs.org
- **Clerk:** https://clerk.com
- **Anthropic:** https://anthropic.com
- **TWIC:** https://theweekinchess.com/twic

## 📧 Support

For issues or questions:
- Create an issue in the repository
- Refer to [SETUP.md](./SETUP.md) for troubleshooting

---

**Status:** Phase 1 Foundation ✅ Complete | Phase 2 Authentication 🔜 Next
