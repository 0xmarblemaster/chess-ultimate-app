# ChessGame Collection Schema Documentation

## Overview

The ChessGame collection in Weaviate contains a comprehensive schema that captures **ALL** information available in PGN (Portable Game Notation) files, plus additional computed fields for enhanced analysis and search capabilities.

## Schema Analysis Results

Based on analysis of `twic1590.pgn` (6,431 games), the following PGN fields were identified:

| Field | Count | Percentage | Description |
|-------|-------|------------|-------------|
| Event | 6,431 | 100% | Tournament/event name |
| Site | 6,431 | 100% | Location |
| Date | 6,431 | 100% | Game date |
| Round | 6,431 | 100% | Round identifier |
| White | 6,431 | 100% | White player name |
| Black | 6,431 | 100% | Black player name |
| Result | 6,431 | 100% | Game result |
| EventDate | 6,431 | 100% | Event start date |
| WhiteFideId | 6,421 | 99.8% | White player FIDE ID |
| BlackFideId | 6,421 | 99.8% | Black player FIDE ID |
| Opening | 6,408 | 99.6% | Opening name |
| ECO | 6,408 | 99.6% | ECO code |
| WhiteElo | 6,375 | 99.1% | White player rating |
| BlackElo | 6,374 | 99.1% | Black player rating |
| BlackTitle | 5,236 | 81.4% | Black player title |
| WhiteTitle | 5,235 | 81.4% | White player title |
| Variation | 4,073 | 63.3% | Opening variation |
| WhiteTeam | 851 | 13.2% | White player team |
| BlackTeam | 851 | 13.2% | Black player team |
| EventType | 441 | 6.9% | Event type (e.g., "team") |

## Complete Schema Structure

### 🎯 Core PGN Fields (39 total properties)

#### 📋 Standard PGN Headers (10 fields)
- **event** (text) - Tournament or event name
- **site** (text) - Location of the event  
- **date** (text) - Game date in PGN format (YYYY.MM.DD)
- **date_utc** (date) - Game date converted to UTC datetime
- **round** (text) - Round number or identifier
- **white_player** (text) - Name of the white player
- **black_player** (text) - Name of the black player
- **result** (text) - Game result (1-0, 0-1, 1/2-1/2, *)
- **event_date** (text) - Event start date in PGN format
- **event_date_utc** (date) - Event start date converted to UTC

#### 👥 Player Information (6 fields)
- **white_title** (text) - White player title (GM, IM, FM, CM, etc.)
- **black_title** (text) - Black player title
- **white_elo** (number) - White player ELO rating
- **black_elo** (number) - Black player ELO rating
- **white_fide_id** (text) - White player FIDE ID
- **black_fide_id** (text) - Black player FIDE ID

#### 🏆 Team Information (3 fields)
- **white_team** (text) - White player team name (team events)
- **black_team** (text) - Black player team name (team events)
- **event_type** (text) - Event type (team, swiss, round-robin)

#### ♟️ Chess-Specific Information (4 fields)
- **eco** (text) - ECO (Encyclopedia of Chess Openings) code
- **opening** (text) - Opening name
- **variation** (text) - Specific opening variation
- **ply_count** (number) - Total number of half-moves

#### 🎯 Position Data (3 fields)
- **final_fen** (text) - FEN of the final position
- **mid_game_fen** (text) - FEN around move 10-15 for position search
- **all_ply_fens** (text[]) - Ordered list of FEN strings for each ply

#### 📝 Move Data (3 fields)
- **pgn_moves** (text) - Full PGN move text with numbers
- **moves_san** (text[]) - Array of moves in Standard Algebraic Notation
- **moves_uci** (text[]) - Array of moves in UCI notation

#### 🔍 Computed Analysis Fields (3 fields)
- **game_length_category** (text) - short (<30), medium (30-60), long (>60)
- **player_strength_category** (text) - master (>2400), expert (2200-2400), etc.
- **opening_family** (text) - Opening family from ECO (Sicilian, French, etc.)

#### ⚙️ System Fields (5 fields)
- **type** (text) - Object type, always 'chess_game'
- **source_file** (text) - Source PGN filename
- **game_index** (number) - Index within source file (0-based)
- **created_at** (date) - Record creation timestamp
- **updated_at** (date) - Last update timestamp

#### 🔎 Search Helper Fields (2 fields)
- **searchable_text** (text) - Combined searchable text for full-text search
- **tags** (text[]) - Searchable tags (endgame, tactics, blunder, etc.)

## Vectorization Configuration

- **Vectorizer**: OpenAI text2vec (text-embedding-3-small)
- **Inverted Index**: BM25 with k1=1.2, b=0.75
- **Skip Vectorization**: System fields, IDs, arrays for performance

## Usage Examples

### Basic Queries
```python
# Count all games
collection.aggregate.over_all(total_count=True)

# Find games by player
collection.query.bm25(query="Magnus Carlsen", limit=10)

# Find games by opening
collection.query.bm25(query="Sicilian Defence", limit=10)
```

### Advanced Filtering
```python
# Games between strong players
collection.query.fetch_objects(
    where=weaviate.classes.query.Filter.by_property("white_elo").greater_than(2600) &
          weaviate.classes.query.Filter.by_property("black_elo").greater_than(2600)
)

# Team tournament games
collection.query.fetch_objects(
    where=weaviate.classes.query.Filter.by_property("event_type").equal("team")
)
```

### Position-Based Search
```python
# Find games with specific position
collection.query.bm25(
    query="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
    query_properties=["all_ply_fens"]
)
```

## Data Loading

To load games into this schema:
```bash
python -m etl.games_loader
```

## Schema Creation

To recreate this schema:
```bash
python create_complete_chess_game_schema.py
```

## Files

- `create_complete_chess_game_schema.py` - Schema creation script
- `count_games_simple.py` - Game counting utility
- `etl/games_loader.py` - Data loading script
- `models/game.py` - Python model definition

## Next Steps

1. **Load Data**: Use the games loader to populate the collection
2. **Build Queries**: Create search and analysis queries
3. **Add Indexes**: Optimize for specific query patterns
4. **Extend Analysis**: Add more computed fields as needed

---

*Schema created: 2025-01-27*  
*Total Properties: 39*  
*Source Analysis: twic1590.pgn (6,431 games)* 