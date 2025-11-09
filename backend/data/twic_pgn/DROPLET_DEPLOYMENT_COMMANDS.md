# TWIC Processing - Droplet Deployment Commands

Since you're now in Claude Code on the droplet, run these commands:

## 1. Setup Python Environment
```bash
cd ~/chessmind-twic
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install chess requests tqdm python-dotenv
```

## 2. Create TWIC Downloader Script
Create `twic-downloader.py` with the content from your local version, or ask Claude Code to:
- Read the script from your local files
- Recreate it in the droplet environment

## 3. Create PGN Concatenator Script
Create `pgn-concatenator.py` in the droplet

## 4. Test Setup
```bash
python3 twic-downloader.py --status
```

## 5. Start Small Test
```bash
# Test with just 5 recent files first
python3 twic-downloader.py --start 1605 --end 1609 --batch-size 5 --extract
```

## 6. Full Download (after test succeeds)
```bash
# Download all TWIC files
python3 twic-downloader.py --start 1 --end 1609 --batch-size 50 --extract --delete-zips
```

## 7. Monitor Progress
```bash
# Check disk usage
df -h
du -sh ~/chessmind-twic/data/*

# Monitor logs (if created)
tail -f ~/chessmind-twic/logs/*.log
```

## 8. Concatenate After Download
```bash
python3 pgn-concatenator.py
```