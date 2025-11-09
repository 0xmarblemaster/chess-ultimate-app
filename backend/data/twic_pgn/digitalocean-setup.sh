#!/bin/bash
# DigitalOcean Droplet Setup Script for TWIC Processing
# Run this script after SSH into your new droplet

set -e  # Exit on any error

echo "🌊 Starting DigitalOcean TWIC Processing Setup..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
apt install -y \
    curl \
    wget \
    git \
    htop \
    unzip \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    software-properties-common

# Create project directory
echo "📁 Creating project directory..."
mkdir -p ~/chessmind-twic
cd ~/chessmind-twic

# Setup Python virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install required packages
pip install --upgrade pip
pip install \
    chess \
    requests \
    tqdm \
    python-dotenv

# Create directory structure
echo "📂 Creating directory structure..."
mkdir -p data/{raw,processed,combined,logs}
mkdir -p scripts/{download,process,monitor}

# Setup monitoring script
cat > ~/chessmind-twic/scripts/monitor/system_status.sh << 'EOF'
#!/bin/bash
echo "=== DigitalOcean TWIC Processing Status ==="
echo "Time: $(date)"
echo "Droplet Info:"
curl -s http://169.254.169.254/metadata/v1/hostname
echo ""
echo "Disk Usage:"
df -h /
echo ""
echo "Memory Usage:"
free -h
echo ""
echo "Data Directory Sizes:"
du -sh ~/chessmind-twic/data/* 2>/dev/null || echo "No data yet"
echo ""
echo "Active Processes:"
ps aux | grep -E "(python|download|process)" | grep -v grep
echo "=================================="
EOF
chmod +x ~/chessmind-twic/scripts/monitor/system_status.sh

# Create useful aliases
echo "⚙️ Setting up aliases..."
cat >> ~/.bashrc << 'EOF'

# TWIC Processing aliases
alias twic='cd ~/chessmind-twic && source venv/bin/activate'
alias twic-status='df -h && du -sh ~/chessmind-twic/data/* 2>/dev/null'
alias twic-monitor='~/chessmind-twic/scripts/monitor/system_status.sh'
EOF

# Display droplet information
echo "✅ DigitalOcean Droplet Setup Complete!"
echo ""
echo "🖥️ Droplet Information:"
echo "Hostname: $(curl -s http://169.254.169.254/metadata/v1/hostname)"
echo "Public IP: $(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)"
echo "Private IP: $(curl -s http://169.254.169.254/metadata/v1/interfaces/private/0/ipv4/address 2>/dev/null || echo 'N/A')"
echo ""
echo "💾 Storage Information:"
df -h /
echo ""
echo "📋 Next Steps:"
echo "1. Upload your TWIC scripts to ~/chessmind-twic/"
echo "2. Run 'source ~/.bashrc' to activate aliases"
echo "3. Run 'twic' to enter project directory with activated Python environment"
echo "4. Start TWIC downloads"
echo ""
echo "🔧 Useful Commands:"
echo "- twic-status: Check disk usage"
echo "- twic-monitor: Full system status"
echo ""
echo "🎯 Ready for TWIC processing!"