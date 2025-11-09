# TWIC Database Expansion - VPS Deployment Guide

## Overview
Complete system for downloading and processing all TWIC chess game archives (1-1609) with approximately 10.6GB storage requirement.

## VPS Requirements (Hetzner CPX31 Recommended)
- **CPU**: 4 vCPU
- **RAM**: 8GB
- **Storage**: 160GB SSD
- **Cost**: ~€24.90/month
- **Bandwidth**: 20TB included

## Deployment Steps

### 1. Initial VPS Setup
```bash
# After SSH into new VPS, run:
chmod +x vps-setup.sh
./vps-setup.sh
```

### 2. Upload Scripts
```bash
# Copy these files to VPS:
scp vps-setup.sh twic-downloader.py pgn-concatenator.py user@your-vps-ip:~/
```

### 3. Environment Activation
```bash
source ~/.bashrc
twic  # Go to project directory
activate  # Activate Python virtual environment
```

### 4. Install Python Dependencies
```bash
pip install chess requests tqdm python-dotenv psycopg2-binary aiohttp
```

### 5. Start TWIC Download
```bash
# Download all TWIC files (1-1609) with extraction
python3 twic-downloader.py --start 1 --end 1609 --batch-size 50 --extract --delete-zips

# Monitor progress
twic-status  # Check disk usage
twic-logs    # Monitor download logs
```

### 6. Concatenate All Files
```bash
# After downloads complete
python3 pgn-concatenator.py
```

## Monitoring Commands
- `twic-status`: Check disk usage and data sizes
- `twic-logs`: Monitor download progress in real-time
- `~/chessmind-twic/scripts/monitor/system_status.sh`: Full system status

## Expected Results
- **Total Games**: ~2.5 million chess games
- **Raw Storage**: ~10.6GB PGN files
- **Download Time**: 6-12 hours (depending on connection)
- **Final Database**: Single concatenated PGN file ready for vector processing

## Recovery and Resume
The system supports automatic resume capability. If interrupted:
```bash
python3 twic-downloader.py --resume --extract --delete-zips
```

## Next Steps
After successful database creation, you can:
1. Transfer the combined PGN file back to your local development environment
2. Process it through your existing ETL pipeline for Weaviate vector database
3. Scale up your vector database infrastructure as needed

## Cost Optimization
- Use `--delete-zips` flag to automatically remove ZIP files after extraction
- Monitor disk usage regularly with `twic-status`
- Consider upgrading storage if needed (Hetzner allows easy volume expansion)