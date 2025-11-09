#!/usr/bin/env python3
"""
ChessMind PGN Concatenator
Combines all TWIC PGN files into organized databases
Optimized for memory efficiency and large datasets
"""

import os
import sys
import json
import logging
import chess.pgn
from pathlib import Path
from typing import Dict, List, Optional, Generator, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import gc
from collections import defaultdict
from tqdm import tqdm

@dataclass
class GameMetadata:
    """Chess game metadata"""
    event: str = ""
    site: str = ""
    date: str = ""
    round: str = ""
    white: str = ""
    black: str = ""
    result: str = ""
    white_elo: str = ""
    black_elo: str = ""
    eco: str = ""
    opening: str = ""
    variation: str = ""
    time_control: str = ""
    termination: str = ""
    source_twic: int = 0
    game_hash: str = ""

@dataclass
class DatabaseStats:
    """Statistics for the combined database"""
    total_games: int = 0
    total_files_processed: int = 0
    duplicate_games: int = 0
    invalid_games: int = 0
    date_range: Tuple[str, str] = ("", "")
    top_events: Dict[str, int] = None
    top_players: Dict[str, int] = None
    processing_time: float = 0.0
    combined_file_size: int = 0

    def __post_init__(self):
        if self.top_events is None:
            self.top_events = {}
        if self.top_players is None:
            self.top_players = {}

class PGNConcatenator:
    """Efficiently concatenate and organize PGN files from TWIC"""

    def __init__(self, base_dir: str = "~/chessmind-twic"):
        self.base_dir = Path(base_dir).expanduser()
        self.processed_dir = self.base_dir / "data" / "processed"
        self.combined_dir = self.base_dir / "data" / "combined"
        self.logs_dir = self.base_dir / "logs"

        # Create directories
        self.combined_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        log_file = self.logs_dir / "pgn_concatenation.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Statistics tracking
        self.stats = DatabaseStats()
        self.game_hashes = set()  # For duplicate detection
        self.event_counts = defaultdict(int)
        self.player_counts = defaultdict(int)
        self.year_counts = defaultdict(int)

        # Configuration
        self.chunk_size = 1000  # Games to process before writing
        self.max_memory_mb = 1024  # Maximum memory usage in MB
        self.validate_games = True  # Validate game format
        self.remove_duplicates = True  # Remove duplicate games

    def find_pgn_files(self) -> List[Path]:
        """Find all PGN files in the processed directory"""
        pgn_files = list(self.processed_dir.glob("*.pgn"))
        pgn_files.sort(key=lambda x: self.extract_twic_number(x.name))

        self.logger.info(f"Found {len(pgn_files)} PGN files to process")
        return pgn_files

    def extract_twic_number(self, filename: str) -> int:
        """Extract TWIC number from filename"""
        try:
            # Extract number from filename like "twic1234.pgn"
            import re
            match = re.search(r'twic(\d+)', filename)
            return int(match.group(1)) if match else 0
        except:
            return 0

    def generate_game_hash(self, game: chess.pgn.Game) -> str:
        """Generate a unique hash for a game to detect duplicates"""
        try:
            # Create hash from key game components
            white = game.headers.get("White", "").strip()
            black = game.headers.get("Black", "").strip()
            date = game.headers.get("Date", "").strip()
            site = game.headers.get("Site", "").strip()
            result = game.headers.get("Result", "").strip()

            # Get first 10 moves for uniqueness
            moves = []
            board = chess.Board()
            game_moves = game.mainline_moves()
            for i, move in enumerate(game_moves):
                if i >= 20:  # First 10 moves (20 plies)
                    break
                moves.append(str(move))
                board.push(move)

            hash_string = f"{white}|{black}|{date}|{site}|{result}|{''.join(moves)}"
            return hashlib.md5(hash_string.encode()).hexdigest()

        except Exception as e:
            self.logger.warning(f"Could not generate hash for game: {e}")
            return ""

    def extract_game_metadata(self, game: chess.pgn.Game, twic_number: int) -> GameMetadata:
        """Extract metadata from a chess game"""
        headers = game.headers

        metadata = GameMetadata(
            event=headers.get("Event", "").strip(),
            site=headers.get("Site", "").strip(),
            date=headers.get("Date", "").strip(),
            round=headers.get("Round", "").strip(),
            white=headers.get("White", "").strip(),
            black=headers.get("Black", "").strip(),
            result=headers.get("Result", "").strip(),
            white_elo=headers.get("WhiteElo", "").strip(),
            black_elo=headers.get("BlackElo", "").strip(),
            eco=headers.get("ECO", "").strip(),
            opening=headers.get("Opening", "").strip(),
            variation=headers.get("Variation", "").strip(),
            time_control=headers.get("TimeControl", "").strip(),
            termination=headers.get("Termination", "").strip(),
            source_twic=twic_number,
            game_hash=self.generate_game_hash(game)
        )

        return metadata

    def validate_game(self, game: chess.pgn.Game) -> bool:
        """Validate that a game is properly formatted"""
        try:
            # Check for required headers
            if not game.headers.get("White") or not game.headers.get("Black"):
                return False

            if not game.headers.get("Result") or game.headers.get("Result") not in ["1-0", "0-1", "1/2-1/2", "*"]:
                return False

            # Try to replay the game to check for illegal moves
            board = chess.Board()
            for move in game.mainline_moves():
                if move not in board.legal_moves:
                    return False
                board.push(move)

            return True

        except Exception as e:
            self.logger.debug(f"Game validation failed: {e}")
            return False

    def process_pgn_file(self, pgn_path: Path) -> Generator[Tuple[chess.pgn.Game, GameMetadata], None, None]:
        """Process a single PGN file and yield games with metadata"""
        twic_number = self.extract_twic_number(pgn_path.name)

        try:
            with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as pgn_file:
                while True:
                    game = chess.pgn.read_game(pgn_file)
                    if game is None:
                        break

                    # Validate game if enabled
                    if self.validate_games and not self.validate_game(game):
                        self.stats.invalid_games += 1
                        continue

                    # Extract metadata
                    metadata = self.extract_game_metadata(game, twic_number)

                    # Check for duplicates
                    if self.remove_duplicates and metadata.game_hash:
                        if metadata.game_hash in self.game_hashes:
                            self.stats.duplicate_games += 1
                            continue
                        self.game_hashes.add(metadata.game_hash)

                    # Update statistics
                    self.update_statistics(metadata)

                    yield game, metadata

        except Exception as e:
            self.logger.error(f"Error processing {pgn_path}: {e}")

    def update_statistics(self, metadata: GameMetadata):
        """Update running statistics"""
        self.stats.total_games += 1

        # Count events and players
        if metadata.event:
            self.event_counts[metadata.event] += 1
        if metadata.white:
            self.player_counts[metadata.white] += 1
        if metadata.black:
            self.player_counts[metadata.black] += 1

        # Count by year
        if metadata.date and len(metadata.date) >= 4:
            year = metadata.date[:4]
            if year.isdigit():
                self.year_counts[year] += 1

    def write_games_chunk(self, games_chunk: List[Tuple[chess.pgn.Game, GameMetadata]], output_file):
        """Write a chunk of games to output file"""
        for game, metadata in games_chunk:
            try:
                # Add source information to headers
                game.headers["SourceTWIC"] = str(metadata.source_twic)
                if metadata.game_hash:
                    game.headers["GameHash"] = metadata.game_hash

                # Write game to file
                print(game, file=output_file)
                print("", file=output_file)  # Empty line between games

            except Exception as e:
                self.logger.error(f"Error writing game: {e}")

    def concatenate_all(self, output_filename: str = "twic_complete_database.pgn") -> Path:
        """Concatenate all PGN files into a single database"""
        start_time = datetime.now()
        output_path = self.combined_dir / output_filename

        self.logger.info(f"Starting concatenation to {output_path}")

        pgn_files = self.find_pgn_files()
        if not pgn_files:
            self.logger.error("No PGN files found to process")
            return output_path

        games_chunk = []

        try:
            with open(output_path, 'w', encoding='utf-8') as output_file:
                # Write database header
                header = f"""[Event "ChessMind Complete TWIC Database"]
[Site "Generated from TWIC 1-{self.extract_twic_number(pgn_files[-1].name)}"]
[Date "{datetime.now().strftime('%Y.%m.%d')}"]
[Round "Database"]
[White "ChessMind"]
[Black "Database"]
[Result "*"]
[Source "The Week In Chess (TWIC)"]
[Generator "ChessMind PGN Concatenator v1.0"]

*

"""
                output_file.write(header)

                # Process files with progress bar
                with tqdm(total=len(pgn_files), desc="Processing TWIC files") as pbar:
                    for pgn_file in pgn_files:
                        self.logger.info(f"Processing {pgn_file.name}")
                        file_games = 0

                        for game, metadata in self.process_pgn_file(pgn_file):
                            games_chunk.append((game, metadata))
                            file_games += 1

                            # Write chunk when it reaches chunk_size
                            if len(games_chunk) >= self.chunk_size:
                                self.write_games_chunk(games_chunk, output_file)
                                games_chunk.clear()

                                # Force garbage collection to manage memory
                                gc.collect()

                        self.stats.total_files_processed += 1
                        self.logger.info(f"Processed {pgn_file.name}: {file_games} games")
                        pbar.update(1)

                # Write remaining games
                if games_chunk:
                    self.write_games_chunk(games_chunk, output_file)

        except Exception as e:
            self.logger.error(f"Error during concatenation: {e}")
            return output_path

        # Finalize statistics
        self.stats.processing_time = (datetime.now() - start_time).total_seconds()
        self.stats.combined_file_size = output_path.stat().st_size
        self.stats.top_events = dict(sorted(self.event_counts.items(), key=lambda x: x[1], reverse=True)[:20])
        self.stats.top_players = dict(sorted(self.player_counts.items(), key=lambda x: x[1], reverse=True)[:50])

        # Get date range
        years = [int(y) for y in self.year_counts.keys() if y.isdigit()]
        if years:
            self.stats.date_range = (str(min(years)), str(max(years)))

        self.save_statistics()
        self.logger.info(f"Concatenation complete! Output: {output_path}")

        return output_path

    def create_yearly_databases(self) -> Dict[str, Path]:
        """Create separate databases for each year"""
        self.logger.info("Creating yearly databases...")

        yearly_files = {}
        yearly_writers = {}

        try:
            pgn_files = self.find_pgn_files()

            # Process all files and sort games by year
            with tqdm(total=len(pgn_files), desc="Creating yearly databases") as pbar:
                for pgn_file in pgn_files:
                    for game, metadata in self.process_pgn_file(pgn_file):
                        # Extract year
                        year = "unknown"
                        if metadata.date and len(metadata.date) >= 4:
                            year_str = metadata.date[:4]
                            if year_str.isdigit():
                                year = year_str

                        # Create writer for this year if not exists
                        if year not in yearly_writers:
                            yearly_path = self.combined_dir / f"twic_{year}_games.pgn"
                            yearly_files[year] = yearly_path
                            yearly_writers[year] = open(yearly_path, 'w', encoding='utf-8')

                        # Write game
                        game.headers["SourceTWIC"] = str(metadata.source_twic)
                        print(game, file=yearly_writers[year])
                        print("", file=yearly_writers[year])

                    pbar.update(1)

        finally:
            # Close all files
            for writer in yearly_writers.values():
                writer.close()

        self.logger.info(f"Created {len(yearly_files)} yearly databases")
        return yearly_files

    def save_statistics(self):
        """Save concatenation statistics"""
        stats_file = self.combined_dir / "database_statistics.json"

        try:
            stats_dict = asdict(self.stats)
            with open(stats_file, 'w') as f:
                json.dump(stats_dict, f, indent=2)

            self.logger.info(f"Statistics saved to {stats_file}")

        except Exception as e:
            self.logger.error(f"Error saving statistics: {e}")

    def print_statistics(self):
        """Print current statistics"""
        print(f"\n{'='*50}")
        print(f"TWIC Database Concatenation Statistics")
        print(f"{'='*50}")
        print(f"Total games processed: {self.stats.total_games:,}")
        print(f"Files processed: {self.stats.total_files_processed}")
        print(f"Duplicate games removed: {self.stats.duplicate_games:,}")
        print(f"Invalid games skipped: {self.stats.invalid_games:,}")
        print(f"Date range: {self.stats.date_range[0]} - {self.stats.date_range[1]}")
        print(f"Combined file size: {self.stats.combined_file_size / 1024 / 1024:.1f} MB")
        print(f"Processing time: {self.stats.processing_time:.1f} seconds")

        if self.stats.top_events:
            print(f"\nTop 10 Events:")
            for event, count in list(self.stats.top_events.items())[:10]:
                print(f"  {event}: {count:,} games")

        if self.stats.top_players:
            print(f"\nTop 10 Players:")
            for player, count in list(self.stats.top_players.items())[:10]:
                print(f"  {player}: {count:,} games")

        print(f"{'='*50}\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='ChessMind PGN Concatenator')
    parser.add_argument('--output', default='twic_complete_database.pgn',
                       help='Output filename (default: twic_complete_database.pgn)')
    parser.add_argument('--yearly', action='store_true',
                       help='Also create yearly databases')
    parser.add_argument('--no-validation', action='store_true',
                       help='Skip game validation (faster)')
    parser.add_argument('--keep-duplicates', action='store_true',
                       help='Keep duplicate games')
    parser.add_argument('--chunk-size', type=int, default=1000,
                       help='Chunk size for processing (default: 1000)')
    parser.add_argument('--stats-only', action='store_true',
                       help='Show statistics from previous run')

    args = parser.parse_args()

    # Initialize concatenator
    concatenator = PGNConcatenator()
    concatenator.validate_games = not args.no_validation
    concatenator.remove_duplicates = not args.keep_duplicates
    concatenator.chunk_size = args.chunk_size

    if args.stats_only:
        # Try to load existing stats
        stats_file = concatenator.combined_dir / "database_statistics.json"
        if stats_file.exists():
            with open(stats_file) as f:
                stats_data = json.load(f)
                concatenator.stats = DatabaseStats(**stats_data)
                concatenator.print_statistics()
        else:
            print("No statistics file found. Run concatenation first.")
        return

    print("🚀 Starting PGN concatenation...")
    print(f"Validation: {'Enabled' if concatenator.validate_games else 'Disabled'}")
    print(f"Duplicate removal: {'Enabled' if concatenator.remove_duplicates else 'Disabled'}")
    print(f"Chunk size: {concatenator.chunk_size}")

    try:
        # Main concatenation
        output_path = concatenator.concatenate_all(args.output)
        print(f"✅ Main database created: {output_path}")

        # Create yearly databases if requested
        if args.yearly:
            yearly_files = concatenator.create_yearly_databases()
            print(f"✅ Created {len(yearly_files)} yearly databases")

        # Show statistics
        concatenator.print_statistics()

    except KeyboardInterrupt:
        print("\n⏹️ Concatenation interrupted by user")
        concatenator.save_statistics()

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        concatenator.save_statistics()


if __name__ == "__main__":
    main()