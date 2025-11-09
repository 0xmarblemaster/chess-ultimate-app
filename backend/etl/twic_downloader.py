#!/usr/bin/env python3
"""
TWIC (The Week in Chess) Complete Archive Downloader
===================================================

This script downloads all available PGN files from The Week in Chess archive
and concatenates them in chronological order to create a comprehensive database.

Features:
- Discovers all available TWIC archives automatically
- Downloads PGN files in parallel for speed
- Sorts games chronologically 
- Removes duplicates based on game signature
- Provides resume capability for interrupted downloads
- Integrates with existing Weaviate games loader

Author: Auto-generated for chess database expansion
Created: 2024
"""

import os
import re
import requests
import gzip
import zipfile
import chess.pgn
import datetime
import hashlib
import time
import json
import concurrent.futures
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path
import logging
from dataclasses import dataclass, asdict

# Import existing configuration
try:
    from . import config as etl_config
except ImportError:
    # Fallback for direct execution
    import config as etl_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twic_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TWICArchive:
    """Represents a TWIC archive with metadata"""
    number: int
    url: str
    filename: str
    size: Optional[int] = None
    downloaded: bool = False
    processed: bool = False
    game_count: Optional[int] = None
    date_range: Optional[str] = None

class TWICDownloader:
    """Main class for downloading and processing TWIC archives"""
    
    def __init__(self, base_url: str = "https://theweekinchess.com/twic"):
        self.base_url = base_url
        self.data_dir = Path(etl_config.PGN_DATA_DIR)
        self.download_dir = self.data_dir / "twic_downloads"
        self.processed_dir = self.data_dir / "twic_processed"  
        self.combined_dir = self.data_dir / "twic_combined"
        self.state_file = self.data_dir / "twic_download_state.json"
        
        # Create directories
        for directory in [self.download_dir, self.processed_dir, self.combined_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        self.session = requests.Session()
        # Use proper browser headers to avoid 406 errors
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Load or initialize state
        self.state = self._load_state()
        
    def _load_state(self) -> Dict:
        """Load download state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning("Could not load state file, starting fresh")
        
        return {
            'discovered_archives': [],
            'last_discovery': None,
            'download_progress': {},
            'processing_progress': {},
            'combined_files': []
        }
    
    def _save_state(self):
        """Save current state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def discover_archives(self) -> List[TWICArchive]:
        """
        Discover all available TWIC archives by testing URL patterns
        
        This method uses binary search to efficiently find the current range
        of available TWIC archives, then builds the complete list.
        
        Returns:
            List of TWICArchive objects sorted by TWIC number
        """
        logger.info("🔍 Discovering TWIC archives...")
        archives = []
        
        # Known patterns for TWIC URLs
        base_patterns = [
            "https://theweekinchess.com/zips/twic{number}g.zip",  # Current format
            "https://theweekinchess.com/zips/twic{number}.zip",   # Alternative format
        ]
        
        # Binary search to find the highest available TWIC number
        logger.info("Finding latest TWIC number...")
        max_twic = self._find_latest_twic_number(base_patterns)
        
        if max_twic == 0:
            logger.error("❌ Could not find any TWIC archives")
            return []
            
        logger.info(f"📊 Latest TWIC found: #{max_twic}")
        
        # Now discover all archives from 1 to max_twic
        logger.info(f"🔍 Checking archives from TWIC #1 to #{max_twic}...")
        
        for twic_num in range(1, max_twic + 1):
            for pattern in base_patterns:
                url = pattern.format(number=twic_num)
                
                # Test if this URL exists
                if self._test_url_exists(url):
                    filename = f"twic{twic_num}{'g' if 'g.zip' in pattern else ''}.zip"
                    archive = TWICArchive(
                        number=twic_num,
                        url=url,
                        filename=filename
                    )
                    archives.append(archive)
                    logger.info(f"✅ Found TWIC #{twic_num}: {url}")
                    break  # Found it with this pattern, move to next number
            
            # Progress indicator every 50 archives
            if twic_num % 50 == 0:
                logger.info(f"📈 Checked up to TWIC #{twic_num}...")
        
        logger.info(f"🎉 Discovery complete! Found {len(archives)} TWIC archives")
        return archives
    
    def _find_latest_twic_number(self, patterns: List[str]) -> int:
        """
        Use binary search to efficiently find the latest TWIC number
        
        Args:
            patterns: List of URL patterns to test
            
        Returns:
            Latest TWIC number found, or 0 if none found
        """
        # Start with a reasonable upper bound
        low, high = 1, 2000
        
        # First, find a reasonable upper bound by doubling
        while high <= 3000:  # Reasonable safety limit
            found = False
            for pattern in patterns:
                url = pattern.format(number=high)
                if self._test_url_exists(url):
                    found = True
                    break
            
            if found:
                low = high
                high *= 2
            else:
                break
        
        # Now binary search between low and high
        latest = 0
        while low <= high:
            mid = (low + high) // 2
            found = False
            
            for pattern in patterns:
                url = pattern.format(number=mid)
                if self._test_url_exists(url):
                    found = True
                    latest = max(latest, mid)
                    break
            
            if found:
                low = mid + 1
            else:
                high = mid - 1
        
        return latest
    
    def _test_url_exists(self, url: str) -> bool:
        """
        Test if a URL exists without downloading the full content
        
        Args:
            url: URL to test
            
        Returns:
            True if URL exists and is accessible
        """
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"URL test failed for {url}: {e}")
            return False
    
    def download_archive(self, archive: TWICArchive, max_retries: int = 3) -> bool:
        """
        Download a single TWIC archive
        
        Args:
            archive: TWICArchive object to download
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if successful, False otherwise
        """
        download_path = self.download_dir / archive.filename
        
        # Skip if already downloaded
        if download_path.exists():
            logger.debug(f"TWIC {archive.number} already downloaded")
            return True
        
        logger.info(f"Downloading TWIC {archive.number}: {archive.filename}")
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(archive.url, stream=True, timeout=30)
                response.raise_for_status()
                
                # Download with progress
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                if downloaded % (total_size // 10 + 1) == 0:  # Log every 10%
                                    logger.debug(f"TWIC {archive.number}: {progress:.1f}% downloaded")
                
                logger.info(f"TWIC {archive.number} downloaded successfully ({downloaded} bytes)")
                return True
                
            except requests.RequestException as e:
                logger.warning(f"Download attempt {attempt + 1} failed for TWIC {archive.number}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to download TWIC {archive.number} after {max_retries} attempts")
                    
        return False
    
    def download_all_archives(self, archives: List[TWICArchive], max_workers: int = 4) -> List[TWICArchive]:
        """
        Download all archives in parallel
        
        Args:
            archives: List of TWICArchive objects to download
            max_workers: Maximum number of parallel downloads
            
        Returns:
            List of successfully downloaded archives
        """
        logger.info(f"Starting parallel download of {len(archives)} archives with {max_workers} workers")
        
        successful_downloads = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_archive = {
                executor.submit(self.download_archive, archive): archive 
                for archive in archives
            }
            
            # Process completed downloads
            for future in concurrent.futures.as_completed(future_to_archive):
                archive = future_to_archive[future]
                try:
                    success = future.result()
                    if success:
                        successful_downloads.append(archive)
                        # Update state
                        self.state['download_progress'][str(archive.number)] = {
                            'completed': True,
                            'timestamp': datetime.datetime.now().isoformat()
                        }
                    else:
                        logger.error(f"Failed to download TWIC {archive.number}")
                        
                except Exception as e:
                    logger.error(f"Exception during download of TWIC {archive.number}: {e}")
                
                # Save state periodically
                self._save_state()
        
        logger.info(f"Downloaded {len(successful_downloads)} out of {len(archives)} archives")
        return successful_downloads 
    
    def extract_pgn_from_archive(self, archive: TWICArchive) -> Optional[Path]:
        """
        Extract PGN file from downloaded archive
        
        Args:
            archive: TWICArchive object
            
        Returns:
            Path to extracted PGN file or None if failed
        """
        archive_path = self.download_dir / archive.filename
        if not archive_path.exists():
            logger.error(f"Archive file not found: {archive_path}")
            return None
        
        # Determine extraction method based on file extension
        try:
            if archive.filename.endswith('.zip'):
                return self._extract_from_zip(archive_path, archive)
            elif archive.filename.endswith('.gz'):
                return self._extract_from_gzip(archive_path, archive)
            else:
                logger.warning(f"Unknown archive format for {archive.filename}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract {archive.filename}: {e}")
            return None
    
    def _extract_from_zip(self, archive_path: Path, archive: TWICArchive) -> Optional[Path]:
        """Extract PGN from ZIP archive"""
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            # Look for PGN files in the archive
            pgn_files = [f for f in zip_file.namelist() if f.lower().endswith('.pgn')]
            
            if not pgn_files:
                logger.warning(f"No PGN files found in {archive.filename}")
                return None
            
            # Extract the first PGN file (usually there's only one)
            pgn_filename = pgn_files[0]
            extracted_path = self.processed_dir / f"twic{archive.number:04d}.pgn"
            
            with zip_file.open(pgn_filename) as source, open(extracted_path, 'wb') as target:
                target.write(source.read())
            
            logger.info(f"Extracted {pgn_filename} from {archive.filename}")
            return extracted_path
    
    def _extract_from_gzip(self, archive_path: Path, archive: TWICArchive) -> Optional[Path]:
        """Extract PGN from GZIP archive"""
        extracted_path = self.processed_dir / f"twic{archive.number:04d}.pgn"
        
        with gzip.open(archive_path, 'rb') as source, open(extracted_path, 'wb') as target:
            target.write(source.read())
        
        logger.info(f"Extracted {archive.filename}")
        return extracted_path
    
    def analyze_pgn_file(self, pgn_path: Path) -> Dict:
        """
        Analyze a PGN file to extract metadata
        
        Args:
            pgn_path: Path to PGN file
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            'game_count': 0,
            'date_range': {'earliest': None, 'latest': None},
            'players': set(),
            'events': set(),
            'has_errors': False,
            'sample_games': []
        }
        
        try:
            with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as f:
                while True:
                    try:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        
                        analysis['game_count'] += 1
                        
                        # Extract date information
                        date_str = game.headers.get('Date', '????.??.??')
                        if date_str != '????.??.??':
                            try:
                                # Try to parse date for range analysis
                                if '.' in date_str:
                                    date_parts = date_str.split('.')
                                    if len(date_parts) >= 1 and date_parts[0] != '????':
                                        year = int(date_parts[0])
                                        if analysis['date_range']['earliest'] is None or year < analysis['date_range']['earliest']:
                                            analysis['date_range']['earliest'] = year
                                        if analysis['date_range']['latest'] is None or year > analysis['date_range']['latest']:
                                            analysis['date_range']['latest'] = year
                            except (ValueError, IndexError):
                                pass
                        
                        # Collect sample data
                        if analysis['game_count'] <= 5:  # First 5 games as samples
                            analysis['sample_games'].append({
                                'white': game.headers.get('White', 'Unknown'),
                                'black': game.headers.get('Black', 'Unknown'),
                                'event': game.headers.get('Event', 'Unknown'),
                                'date': date_str,
                                'result': game.headers.get('Result', '*')
                            })
                        
                        # Track unique players and events (limited to avoid memory issues)
                        if len(analysis['players']) < 1000:
                            analysis['players'].add(game.headers.get('White', 'Unknown'))
                            analysis['players'].add(game.headers.get('Black', 'Unknown'))
                        
                        if len(analysis['events']) < 100:
                            analysis['events'].add(game.headers.get('Event', 'Unknown'))
                            
                    except Exception as e:
                        logger.debug(f"Error reading game in {pgn_path}: {e}")
                        analysis['has_errors'] = True
                        
        except Exception as e:
            logger.error(f"Failed to analyze {pgn_path}: {e}")
            analysis['has_errors'] = True
        
        # Convert sets to lists for JSON serialization
        analysis['players'] = list(analysis['players'])[:100]  # Limit size
        analysis['events'] = list(analysis['events'])
        
        return analysis
    
    def create_game_signature(self, game: chess.pgn.Game) -> str:
        """
        Create a unique signature for a game to detect duplicates
        
        Args:
            game: chess.pgn.Game object
            
        Returns:
            MD5 hash string representing the game
        """
        # Use key game information to create signature
        signature_data = {
            'white': game.headers.get('White', ''),
            'black': game.headers.get('Black', ''),
            'event': game.headers.get('Event', ''),
            'site': game.headers.get('Site', ''),
            'date': game.headers.get('Date', ''),
            'round': game.headers.get('Round', ''),
            'result': game.headers.get('Result', ''),
        }
        
        # Add first 10 moves to signature to distinguish games with same metadata
        moves = []
        board = game.board()
        for i, move in enumerate(game.mainline_moves()):
            if i >= 10:  # First 10 moves should be enough
                break
            moves.append(board.san(move))
            board.push(move)
        
        signature_data['moves'] = ' '.join(moves)
        
        # Create hash
        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_str.encode()).hexdigest()
    
    def concatenate_pgn_files_chronologically(self, pgn_files: List[Tuple[Path, Dict]], output_file: Path) -> int:
        """
        Concatenate PGN files in chronological order, removing duplicates
        
        Args:
            pgn_files: List of tuples (pgn_path, analysis_data)
            output_file: Path for combined output file
            
        Returns:
            Total number of unique games processed
        """
        logger.info(f"Concatenating {len(pgn_files)} PGN files chronologically")
        
        # Sort files by TWIC number (they should already be chronological)
        pgn_files.sort(key=lambda x: x[1].get('twic_number', 0))
        
        games_by_date = []
        seen_signatures = set()
        total_games = 0
        unique_games = 0
        
        # Collect all games with their dates
        for pgn_path, analysis in pgn_files:
            logger.info(f"Processing {pgn_path.name} ({analysis['game_count']} games)")
            
            try:
                with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as f:
                    while True:
                        try:
                            game = chess.pgn.read_game(f)
                            if game is None:
                                break
                            
                            total_games += 1
                            
                            # Create signature to detect duplicates
                            signature = self.create_game_signature(game)
                            if signature in seen_signatures:
                                logger.debug(f"Duplicate game found: {game.headers.get('White', 'Unknown')} vs {game.headers.get('Black', 'Unknown')}")
                                continue
                            
                            seen_signatures.add(signature)
                            unique_games += 1
                            
                            # Parse date for sorting
                            date_str = game.headers.get('Date', '????.??.??')
                            sort_date = self._parse_date_for_sorting(date_str)
                            
                            games_by_date.append((sort_date, game, pgn_path.name))
                            
                        except Exception as e:
                            logger.debug(f"Error reading game from {pgn_path}: {e}")
                            continue
                            
            except Exception as e:
                logger.error(f"Failed to process {pgn_path}: {e}")
                continue
        
        logger.info(f"Collected {unique_games} unique games out of {total_games} total games")
        
        # Sort games chronologically
        logger.info("Sorting games chronologically...")
        games_by_date.sort(key=lambda x: x[0])
        
        # Write combined file
        logger.info(f"Writing combined file to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, (sort_date, game, source_file) in enumerate(games_by_date):
                if i > 0:
                    f.write('\n\n')  # Separate games with blank lines
                
                # Add source comment
                f.write(f"[%Source \"{source_file}\"]\n")
                
                # Write game
                f.write(str(game))
                
                if (i + 1) % 1000 == 0:
                    logger.info(f"Written {i + 1} games to combined file")
        
        logger.info(f"Successfully created combined PGN file with {unique_games} games")
        return unique_games
    
    def _parse_date_for_sorting(self, date_str: str) -> datetime.datetime:
        """
        Parse PGN date string into datetime for sorting
        
        Args:
            date_str: Date string from PGN header
            
        Returns:
            datetime object (with defaults for missing parts)
        """
        if date_str == '????.??.??':
            return datetime.datetime(1900, 1, 1)  # Very old date for unknown dates
        
        parts = date_str.split('.')
        year = int(parts[0]) if parts[0] != '????' else 1900
        month = int(parts[1]) if len(parts) > 1 and parts[1] != '??' else 1
        day = int(parts[2]) if len(parts) > 2 and parts[2] != '??' else 1
        
        try:
            return datetime.datetime(year, month, day)
        except ValueError:
            # Handle invalid dates
            return datetime.datetime(year, 1, 1)
    
    def process_all_archives(self, archives: List[TWICArchive]) -> Path:
        """
        Complete processing pipeline: extract, analyze, and concatenate all archives
        
        Args:
            archives: List of downloaded TWICArchive objects
            
        Returns:
            Path to final combined PGN file
        """
        logger.info(f"Processing {len(archives)} archives")
        
        pgn_files_with_analysis = []
        
        # Extract and analyze each archive
        for archive in archives:
            logger.info(f"Processing TWIC {archive.number}")
            
            # Extract PGN from archive
            pgn_path = self.extract_pgn_from_archive(archive)
            if not pgn_path:
                logger.warning(f"Failed to extract PGN from TWIC {archive.number}")
                continue
            
            # Analyze PGN file
            analysis = self.analyze_pgn_file(pgn_path)
            analysis['twic_number'] = archive.number
            
            logger.info(f"TWIC {archive.number}: {analysis['game_count']} games, "
                       f"date range {analysis['date_range']['earliest']}-{analysis['date_range']['latest']}")
            
            pgn_files_with_analysis.append((pgn_path, analysis))
            
            # Update state
            self.state['processing_progress'][str(archive.number)] = {
                'completed': True,
                'game_count': analysis['game_count'],
                'analysis': analysis,
                'timestamp': datetime.datetime.now().isoformat()
            }
            self._save_state()
        
        # Create combined file
        output_file = self.combined_dir / f"twic_complete_{datetime.datetime.now().strftime('%Y%m%d')}.pgn"
        unique_games = self.concatenate_pgn_files_chronologically(pgn_files_with_analysis, output_file)
        
        # Update state with final result
        self.state['combined_files'].append({
            'filename': output_file.name,
            'path': str(output_file),
            'game_count': unique_games,
            'created': datetime.datetime.now().isoformat(),
            'source_archives': [archive.number for archive in archives]
        })
        self._save_state()
        
        return output_file


def main():
    """Main function to run the complete TWIC download and processing pipeline"""
    downloader = TWICDownloader()
    
    try:
        # Step 1: Discover all available archives
        print("🔍 Discovering TWIC archives...")
        archives = downloader.discover_archives()
        print(f"✅ Discovered {len(archives)} archives")
        
        # Step 2: Download all archives
        print("📥 Downloading archives...")
        successful_downloads = downloader.download_all_archives(archives)
        print(f"✅ Downloaded {len(successful_downloads)} archives")
        
        # Step 3: Process and combine all archives
        print("⚙️ Processing and combining archives...")
        combined_file = downloader.process_all_archives(successful_downloads)
        print(f"✅ Created combined file: {combined_file}")
        
        # Step 4: Display summary
        print(f"\n🎉 TWIC Download Complete!")
        print(f"📁 Combined file: {combined_file}")
        print(f"📊 Total archives processed: {len(successful_downloads)}")
        
        # Get final stats
        if downloader.state['combined_files']:
            latest_combined = downloader.state['combined_files'][-1]
            print(f"🎲 Total unique games: {latest_combined['game_count']}")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Load into Weaviate: python -m games_loader")
        print(f"   2. Combined file location: {combined_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Download interrupted by user")
        print("💾 Progress has been saved and can be resumed")
    except Exception as e:
        logger.error(f"Fatal error in main pipeline: {e}")
        print(f"❌ Error: {e}")
        print("💾 Progress has been saved")


if __name__ == "__main__":
    main() 