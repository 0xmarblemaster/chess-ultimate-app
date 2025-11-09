#!/usr/bin/env python3
"""
TWIC Download Progress Monitor
=============================

This script monitors the progress of the TWIC download process in real-time.
"""

import time
import os
import json
from pathlib import Path
from datetime import datetime

def monitor_progress():
    """Monitor the TWIC download progress"""
    
    # Paths
    downloads_dir = Path("/home/marblemaster/Desktop/Cursor/mvp1/backend/data/twic_pgn/twic_downloads")
    state_file = Path("/home/marblemaster/Desktop/Cursor/mvp1/backend/data/twic_pgn/twic_download_state.json")
    log_file = Path("full_download.log")
    
    print("🔍 TWIC Download Progress Monitor")
    print("=" * 50)
    print(f"📁 Downloads dir: {downloads_dir}")
    print(f"📊 State file: {state_file}")
    print(f"📋 Log file: {log_file}")
    print()
    
    last_count = 0
    start_time = time.time()
    
    while True:
        try:
            # Count downloaded files
            if downloads_dir.exists():
                downloaded_files = list(downloads_dir.glob("*.zip"))
                current_count = len(downloaded_files)
            else:
                current_count = 0
            
            # Read state file if available
            discovered_count = 0
            if state_file.exists():
                try:
                    with open(state_file, 'r') as f:
                        state = json.load(f)
                        discovered_count = len(state.get('discovered_archives', []))
                except:
                    pass
            
            # Read last few lines of log
            latest_log = ""
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            latest_log = lines[-1].strip()
                except:
                    pass
            
            # Calculate progress
            elapsed = time.time() - start_time
            rate = (current_count - last_count) / 60 if elapsed > 60 else 0  # per minute
            
            # Display progress
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\r[{timestamp}] 📥 Downloaded: {current_count:4d} | 🔍 Discovered: {discovered_count:4d} | 📈 Rate: {rate:.1f}/min", end="")
            
            if latest_log and "INFO" in latest_log:
                # Extract just the message part
                if " - INFO - " in latest_log:
                    message = latest_log.split(" - INFO - ", 1)[1]
                    print(f" | 📋 {message[:50]}{'...' if len(message) > 50 else ''}")
                else:
                    print()
            else:
                print()
            
            # Update for next iteration
            if elapsed > 60:  # Reset rate calculation every minute
                last_count = current_count
                start_time = time.time()
            
            time.sleep(10)  # Update every 10 seconds
            
        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_progress() 