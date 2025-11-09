#!/bin/bash
# Upload TWIC scripts to DigitalOcean droplet
# Run this from your local machine

# Replace with your actual droplet IP
DROPLET_IP="your_droplet_ip_here"

echo "🚀 Uploading TWIC scripts to DigitalOcean droplet..."

# Upload all necessary files
scp twic-downloader.py root@$DROPLET_IP:~/chessmind-twic/
scp pgn-concatenator.py root@$DROPLET_IP:~/chessmind-twic/
scp digitalocean-setup.sh root@$DROPLET_IP:~/chessmind-twic/

echo "✅ Upload complete!"
echo ""
echo "📋 Next steps on droplet:"
echo "1. SSH into droplet: ssh root@$DROPLET_IP"
echo "2. Go to project: cd ~/chessmind-twic"
echo "3. Activate environment: source venv/bin/activate"
echo "4. Start download: python3 twic-downloader.py --start 1 --end 1609 --batch-size 50 --extract --delete-zips"