# DigitalOcean + Supabase Integration Plan

## Phase 1: Supabase Database Setup

### Step 1: Configure Supabase Project
1. **Create new Supabase project**
2. **Enable pgvector extension**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. **Create database schema**:
   ```sql
   -- Chess games table with vector search
   CREATE TABLE chess_games (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       pgn TEXT NOT NULL,
       fen TEXT,
       white_player TEXT,
       black_player TEXT,
       event TEXT,
       event_date DATE,
       result TEXT,
       opening_name TEXT,
       opening_eco TEXT,
       time_control TEXT,
       white_elo INTEGER,
       black_elo INTEGER,
       embedding VECTOR(1536),
       metadata JSONB,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );

   -- Vector search index
   CREATE INDEX ON chess_games USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);

   -- Text search indexes
   CREATE INDEX idx_chess_games_players ON chess_games(white_player, black_player);
   CREATE INDEX idx_chess_games_opening ON chess_games(opening_name);
   CREATE INDEX idx_chess_games_date ON chess_games(event_date);
   ```

### Step 2: User Management Tables
```sql
-- User profiles
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    username TEXT UNIQUE,
    chess_rating INTEGER DEFAULT 1200,
    preferred_time_control TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User learning progress
CREATE TABLE user_game_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    game_id UUID REFERENCES chess_games(id),
    analysis_type TEXT, -- 'studied', 'bookmarked', 'practiced'
    notes TEXT,
    difficulty_rating INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Phase 2: DigitalOcean Processing Pipeline

### Step 1: Setup Environment Variables
```bash
# In DigitalOcean droplet
export SUPABASE_URL="your-project-url"
export SUPABASE_ANON_KEY="your-anon-key"
export SUPABASE_SERVICE_KEY="your-service-key"
export OPENAI_API_KEY="your-openai-key"
```

### Step 2: Create Data Processing Scripts

#### A. PGN Parser and Processor
```python
# pgn-processor.py
import chess.pgn
import json
from pathlib import Path

class PGNProcessor:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def process_pgn_file(self, pgn_path):
        """Process single PGN file into structured data"""
        games = []
        with open(pgn_path) as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break

                # Extract game data
                game_data = {
                    'pgn': str(game),
                    'fen': game.board().fen(),
                    'white_player': game.headers.get('White', ''),
                    'black_player': game.headers.get('Black', ''),
                    'event': game.headers.get('Event', ''),
                    'event_date': game.headers.get('Date', ''),
                    'result': game.headers.get('Result', ''),
                    'opening_name': game.headers.get('Opening', ''),
                    'opening_eco': game.headers.get('ECO', ''),
                    'white_elo': self.parse_elo(game.headers.get('WhiteElo')),
                    'black_elo': self.parse_elo(game.headers.get('BlackElo')),
                }
                games.append(game_data)

        return games
```

#### B. Vector Generation
```python
# vector-generator.py
import openai
from typing import List, Dict

class VectorGenerator:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def generate_game_embedding(self, game_data: Dict) -> List[float]:
        """Generate embedding for chess game"""
        # Create descriptive text for embedding
        text = f"""
        Chess Game: {game_data['white_player']} vs {game_data['black_player']}
        Event: {game_data['event']}
        Opening: {game_data['opening_name']}
        Result: {game_data['result']}
        Moves: {game_data['pgn'][:500]}  # First 500 chars
        """

        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=text.strip()
        )
        return response['data'][0]['embedding']
```

#### C. Supabase Uploader
```python
# supabase-uploader.py
from supabase import create_client, Client
import json
from typing import List, Dict

class SupabaseUploader:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    def upload_games_batch(self, games: List[Dict], batch_size: int = 100):
        """Upload games in batches"""
        for i in range(0, len(games), batch_size):
            batch = games[i:i + batch_size]

            try:
                result = self.client.table('chess_games').insert(batch).execute()
                print(f"Uploaded batch {i//batch_size + 1}: {len(batch)} games")
            except Exception as e:
                print(f"Error uploading batch {i//batch_size + 1}: {e}")
```

## Phase 3: Complete Processing Pipeline

### Master Processing Script
```python
# process-all-twic.py
import os
from pgn_processor import PGNProcessor
from vector_generator import VectorGenerator
from supabase_uploader import SupabaseUploader

def main():
    # Initialize components
    processor = PGNProcessor('./data/processed', './data/structured')
    vectorizer = VectorGenerator(os.getenv('OPENAI_API_KEY'))
    uploader = SupabaseUploader(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_KEY')
    )

    # Process all PGN files
    pgn_files = list(Path('./data/processed').glob('*.pgn'))
    total_games_processed = 0

    for pgn_file in pgn_files:
        print(f"Processing {pgn_file.name}...")

        # Parse PGN
        games = processor.process_pgn_file(pgn_file)

        # Generate embeddings
        for game in games:
            game['embedding'] = vectorizer.generate_game_embedding(game)

        # Upload to Supabase
        uploader.upload_games_batch(games)

        total_games_processed += len(games)
        print(f"Total processed: {total_games_processed}")

if __name__ == "__main__":
    main()
```

## Phase 4: Frontend Integration

### API Endpoints (Auto-generated by Supabase)
```javascript
// Search for games
const { data: games } = await supabase
  .from('chess_games')
  .select('*')
  .textSearch('pgn', 'King Indian Defense')
  .limit(10);

// Vector similarity search
const { data: similarGames } = await supabase.rpc('match_games', {
  query_embedding: userQueryEmbedding,
  similarity_threshold: 0.8,
  match_count: 10
});

// User progress tracking
const { data } = await supabase
  .from('user_game_analysis')
  .insert({
    user_id: userId,
    game_id: gameId,
    analysis_type: 'studied',
    notes: 'Learned new opening principle'
  });
```

## Expected Processing Timeline

1. **TWIC Download**: 6-12 hours (DigitalOcean)
2. **PGN Processing**: 4-6 hours (DigitalOcean)
3. **Vector Generation**: 12-24 hours (DigitalOcean + OpenAI API)
4. **Database Upload**: 2-4 hours (DigitalOcean → Supabase)
5. **Total**: ~24-48 hours for complete database

## Cost Breakdown
- **DigitalOcean**: $24/month (processing server)
- **Supabase**: $25/month (Pro plan with pgvector)
- **OpenAI API**: ~$200-400 (one-time for embeddings)
- **Total Monthly**: $49/month after initial setup