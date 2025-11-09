#!/usr/bin/env python3
"""
ChessMind TWIC Mass Downloader
Automatically downloads all TWIC files (1-1609+) with resume capability
Optimized for Hetzner VPS with 160GB storage
"""

import os
import sys
import json
import time
import requests
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures
import threading
from tqdm import tqdm

@dataclass
class TWICFile:
    """Represents a TWIC file with metadata"""
    number: int
    url: str
    local_path: str
    extracted_path: str
    size_bytes: int = 0
    status: str = 'pending'  # pending, downloading, completed, error, extracted
    error_message: str = ''
    download_time: float = 0.0

class TWICDownloader:
    """Mass downloader for TWIC chess game archives"""

    def __init__(self, base_dir: str = "~/chessmind-twic"):
        self.base_dir = Path(base_dir).expanduser()
        self.data_dir = self.base_dir / "data"
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.combined_dir = self.data_dir / "combined"
        self.logs_dir = self.base_dir / "logs"

        # Create directories
        for dir_path in [self.data_dir, self.raw_dir, self.processed_dir, self.combined_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Setup logging
        log_file = self.logs_dir / "twic_download.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Progress tracking
        self.progress_file = self.base_dir / "download_progress.json"
        self.stats_file = self.base_dir / "download_stats.json"
        self.twic_files: Dict[int, TWICFile] = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ChessMind-TWIC-Downloader/1.0 (Educational Chess Database)'
        })

        # Configuration
        self.base_url = "https://theweekinchess.com/zips/"
        self.max_workers = 3  # Conservative to respect server
        self.retry_attempts = 3
        self.delay_between_downloads = 2.0  # Seconds
        self.chunk_size = 8192  # For streaming downloads

        # Load existing progress
        self.load_progress()

    def load_progress(self):
        """Load existing download progress"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    for num_str, file_data in data.items():
                        num = int(num_str)
                        self.twic_files[num] = TWICFile(**file_data)
                self.logger.info(f"Loaded progress for {len(self.twic_files)} TWIC files")
            except Exception as e:
                self.logger.error(f"Error loading progress: {e}")

    def save_progress(self):
        """Save current download progress"""
        try:
            data = {
                str(num): {
                    'number': tf.number,
                    'url': tf.url,
                    'local_path': tf.local_path,
                    'extracted_path': tf.extracted_path,
                    'size_bytes': tf.size_bytes,
                    'status': tf.status,
                    'error_message': tf.error_message,
                    'download_time': tf.download_time
                }
                for num, tf in self.twic_files.items()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving progress: {e}")

    def save_stats(self):
        """Save download statistics"""
        try:
            completed = [tf for tf in self.twic_files.values() if tf.status == 'completed']
            extracted = [tf for tf in self.twic_files.values() if tf.status == 'extracted']
            errors = [tf for tf in self.twic_files.values() if tf.status == 'error']

            stats = {
                'timestamp': datetime.now().isoformat(),
                'total_files': len(self.twic_files),
                'completed_downloads': len(completed),
                'extracted_files': len(extracted),
                'error_count': len(errors),
                'total_downloaded_mb': sum(tf.size_bytes for tf in completed) / 1024 / 1024,
                'total_download_time': sum(tf.download_time for tf in completed),
                'average_download_time': sum(tf.download_time for tf in completed) / len(completed) if completed else 0,
                'errors': [{'number': tf.number, 'error': tf.error_message} for tf in errors]
            }

            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving stats: {e}")

    def initialize_twic_list(self, start: int = 1, end: int = 1609):
        """Initialize the list of TWIC files to download"""
        self.logger.info(f"Initializing TWIC list from {start} to {end}")

        for num in range(start, end + 1):
            if num not in self.twic_files:
                url = f"{self.base_url}twic{num}g.zip"
                local_path = str(self.raw_dir / f"twic{num}g.zip")
                extracted_path = str(self.processed_dir / f"twic{num}.pgn")

                self.twic_files[num] = TWICFile(
                    number=num,
                    url=url,
                    local_path=local_path,
                    extracted_path=extracted_path
                )

        self.logger.info(f"Initialized {len(self.twic_files)} TWIC files for download")
        self.save_progress()

    def check_disk_space(self, required_gb: float = 15.0) -> bool:
        """Check if there's enough disk space for downloads"""
        try:
            stat = os.statvfs(self.base_dir)
            free_gb = (stat.f_bavail * stat.f_frsize) / 1024 / 1024 / 1024

            self.logger.info(f"Free disk space: {free_gb:.1f}GB")

            if free_gb < required_gb:
                self.logger.warning(f"Low disk space! {free_gb:.1f}GB free, {required_gb:.1f}GB required")
                return False
            return True

        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            return False

    def download_file(self, twic_file: TWICFile) -> bool:
        """Download a single TWIC file with resume capability"""
        local_path = Path(twic_file.local_path)

        # Check if already downloaded
        if local_path.exists() and twic_file.status == 'completed':
            self.logger.info(f"TWIC {twic_file.number} already downloaded")
            return True

        # Check if partially downloaded (resume capability)
        resume_header = {}
        if local_path.exists():
            existing_size = local_path.stat().st_size
            resume_header['Range'] = f'bytes={existing_size}-'
            self.logger.info(f"Resuming TWIC {twic_file.number} from byte {existing_size}")

        try:
            twic_file.status = 'downloading'
            start_time = time.time()

            response = self.session.get(
                twic_file.url,
                headers=resume_header,
                stream=True,
                timeout=30
            )
            response.raise_for_status()

            # Get total file size
            if 'content-length' in response.headers:
                total_size = int(response.headers['content-length'])
                if resume_header:
                    total_size += existing_size
            else:
                total_size = 0

            # Download with progress
            mode = 'ab' if resume_header else 'wb'
            with open(local_path, mode) as f:
                downloaded = existing_size if resume_header else 0

                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # Update file info
            twic_file.size_bytes = local_path.stat().st_size
            twic_file.download_time = time.time() - start_time
            twic_file.status = 'completed'
            twic_file.error_message = ''

            self.logger.info(f"Downloaded TWIC {twic_file.number} ({twic_file.size_bytes/1024/1024:.1f}MB in {twic_file.download_time:.1f}s)")
            return True

        except Exception as e:
            twic_file.status = 'error'
            twic_file.error_message = str(e)
            self.logger.error(f"Error downloading TWIC {twic_file.number}: {e}")

            # Clean up partial file on error
            if local_path.exists() and not resume_header:
                local_path.unlink()

            return False

    def extract_pgn(self, twic_file: TWICFile) -> bool:
        """Extract PGN from downloaded ZIP file"""
        if twic_file.status != 'completed':
            return False

        zip_path = Path(twic_file.local_path)
        pgn_path = Path(twic_file.extracted_path)

        # Check if already extracted
        if pgn_path.exists():
            twic_file.status = 'extracted'
            return True

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # Find the PGN file in the archive
                pgn_files = [f for f in zip_file.namelist() if f.endswith('.pgn')]

                if not pgn_files:
                    self.logger.error(f"No PGN file found in TWIC {twic_file.number}")
                    return False

                # Extract the PGN file
                pgn_file = pgn_files[0]  # Take the first PGN file
                with zip_file.open(pgn_file) as source:
                    with open(pgn_path, 'wb') as target:
                        target.write(source.read())

            twic_file.status = 'extracted'
            self.logger.info(f"Extracted TWIC {twic_file.number} -> {pgn_path.name}")

            # Delete ZIP file to save space (optional)
            # zip_path.unlink()

            return True

        except Exception as e:
            self.logger.error(f"Error extracting TWIC {twic_file.number}: {e}")
            return False

    def download_batch(self, batch_size: int = 50, extract: bool = True, delete_zips: bool = False):
        """Download TWIC files in batches to manage disk space"""
        pending_files = [tf for tf in self.twic_files.values() if tf.status == 'pending']

        self.logger.info(f"Starting batch download of {len(pending_files)} files in batches of {batch_size}")

        for i in range(0, len(pending_files), batch_size):
            batch = pending_files[i:i+batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1}: TWIC {batch[0].number} to {batch[-1].number}")

            # Check disk space before each batch
            if not self.check_disk_space(5.0):  # Require 5GB free
                self.logger.error("Insufficient disk space. Stopping download.")
                break

            # Download batch with progress bar
            with tqdm(total=len(batch), desc=f"Batch {i//batch_size + 1}") as pbar:
                for twic_file in batch:
                    # Download
                    if self.download_file(twic_file):
                        # Extract if requested
                        if extract:
                            self.extract_pgn(twic_file)

                        # Delete ZIP if requested and extraction successful
                        if delete_zips and twic_file.status == 'extracted':
                            zip_path = Path(twic_file.local_path)
                            if zip_path.exists():
                                zip_path.unlink()

                    pbar.update(1)

                    # Rate limiting
                    time.sleep(self.delay_between_downloads)

                    # Save progress regularly
                    if twic_file.number % 10 == 0:
                        self.save_progress()
                        self.save_stats()

            self.logger.info(f"Completed batch {i//batch_size + 1}")

        self.save_progress()
        self.save_stats()
        self.logger.info("Batch download complete!")

    def get_download_status(self) -> Dict:
        """Get current download status"""
        total = len(self.twic_files)
        completed = len([tf for tf in self.twic_files.values() if tf.status == 'completed'])
        extracted = len([tf for tf in self.twic_files.values() if tf.status == 'extracted'])
        errors = len([tf for tf in self.twic_files.values() if tf.status == 'error'])
        pending = len([tf for tf in self.twic_files.values() if tf.status == 'pending'])

        return {
            'total': total,
            'completed': completed,
            'extracted': extracted,
            'errors': errors,
            'pending': pending,
            'completion_percentage': (completed + extracted) / total * 100 if total > 0 else 0
        }

    def print_status(self):
        """Print current download status"""
        status = self.get_download_status()

        print(f"\n=== TWIC Download Status ===")
        print(f"Total files: {status['total']}")
        print(f"Downloaded: {status['completed']}")
        print(f"Extracted: {status['extracted']}")
        print(f"Errors: {status['errors']}")
        print(f"Pending: {status['pending']}")
        print(f"Progress: {status['completion_percentage']:.1f}%")

        # Disk usage
        try:
            raw_size = sum(f.stat().st_size for f in self.raw_dir.rglob('*') if f.is_file())
            processed_size = sum(f.stat().st_size for f in self.processed_dir.rglob('*') if f.is_file())

            print(f"\nDisk Usage:")
            print(f"Raw files (ZIP): {raw_size / 1024 / 1024:.1f}MB")
            print(f"Processed files (PGN): {processed_size / 1024 / 1024:.1f}MB")
            print(f"Total: {(raw_size + processed_size) / 1024 / 1024:.1f}MB")

        except Exception as e:
            print(f"Could not calculate disk usage: {e}")

        print("=" * 30)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='ChessMind TWIC Mass Downloader')
    parser.add_argument('--start', type=int, default=1, help='Start TWIC number (default: 1)')
    parser.add_argument('--end', type=int, default=1609, help='End TWIC number (default: 1609)')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size (default: 50)')
    parser.add_argument('--extract', action='store_true', help='Extract PGN files after download')
    parser.add_argument('--delete-zips', action='store_true', help='Delete ZIP files after extraction')
    parser.add_argument('--status', action='store_true', help='Show download status and exit')
    parser.add_argument('--resume', action='store_true', help='Resume previous download')

    args = parser.parse_args()

    # Initialize downloader
    downloader = TWICDownloader()

    if args.status:
        downloader.print_status()
        return

    # Initialize TWIC list
    if not args.resume:
        downloader.initialize_twic_list(args.start, args.end)

    # Check disk space
    if not downloader.check_disk_space():
        print("❌ Insufficient disk space. Please free up space and try again.")
        return

    print("🚀 Starting TWIC download...")
    print(f"Range: TWIC {args.start} to {args.end}")
    print(f"Batch size: {args.batch_size}")
    print(f"Extract PGN: {'Yes' if args.extract else 'No'}")
    print(f"Delete ZIPs: {'Yes' if args.delete_zips else 'No'}")

    # Start download
    try:
        downloader.download_batch(
            batch_size=args.batch_size,
            extract=args.extract,
            delete_zips=args.delete_zips
        )

        print("\n✅ Download complete!")
        downloader.print_status()

    except KeyboardInterrupt:
        print("\n⏹️  Download interrupted by user")
        downloader.save_progress()
        downloader.save_stats()
        print("Progress saved. Use --resume to continue later.")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        downloader.save_progress()
        downloader.save_stats()


if __name__ == "__main__":
    main()