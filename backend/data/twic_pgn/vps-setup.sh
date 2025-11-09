#!/bin/bash
# VPS Setup Script for ChessMind TWIC Processing
# Run this after connecting to your new Hetzner VPS

set -e  # Exit on any error

echo "🚀 Starting ChessMind VPS Setup..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    unzip \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose standalone
echo "🐳 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create project directories
echo "📁 Creating project directories..."
mkdir -p ~/chessmind-twic/{downloads,processed,logs,scripts}
cd ~/chessmind-twic

# Setup Python virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install Python packages for chess processing
pip install \
    chess \
    requests \
    tqdm \
    python-dotenv \
    psycopg2-binary \
    aiohttp \
    asyncio

# Create basic directory structure
echo "📂 Creating directory structure..."
mkdir -p data/{raw,processed,combined,logs}
mkdir -p scripts/{download,process,monitor}

# Setup disk monitoring
echo "💾 Setting up disk monitoring..."
df -h

# Create useful aliases
echo "⚙️ Setting up aliases..."
cat >> ~/.bashrc << 'EOF'

# ChessMind aliases
alias twic='cd ~/chessmind-twic'
alias activate='source ~/chessmind-twic/venv/bin/activate'
alias twic-status='df -h && du -sh ~/chessmind-twic/data/*'
alias twic-logs='tail -f ~/chessmind-twic/logs/download.log'
EOF

# Setup basic monitoring script
cat > ~/chessmind-twic/scripts/monitor/system_status.sh << 'EOF'
#!/bin/bash
echo "=== ChessMind TWIC Processing Status ==="
echo "Time: $(date)"
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

# Create log rotation config
sudo tee /etc/logrotate.d/chessmind-twic << 'EOF'
/home/*/chessmind-twic/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 root root
}
EOF

# Setup firewall (optional but recommended)
echo "🔥 Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw --force enable

echo "✅ VPS Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Run 'source ~/.bashrc' to activate aliases"
echo "2. Run 'twic' to go to project directory"
echo "3. Run 'activate' to activate Python environment"
echo "4. Upload your TWIC download scripts"
echo ""
echo "🔧 Useful Commands:"
echo "- twic-status: Check disk usage and data sizes"
echo "- twic-logs: Monitor download progress"
echo "- ~/chessmind-twic/scripts/monitor/system_status.sh: Full system status"
echo ""
echo "💾 Available Space:"
df -h /
echo ""
echo "🎯 Ready for TWIC processing!"