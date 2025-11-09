#!/bin/bash
# Setup Claude Code inside DigitalOcean droplet
# Run this after basic droplet setup

echo "🤖 Setting up Claude Code in DigitalOcean droplet..."

# Install Node.js (required for Claude Code)
echo "📦 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
apt-get install -y nodejs

# Verify Node.js installation
node --version
npm --version

# Install Claude Code globally
echo "🚀 Installing Claude Code..."
npm install -g @anthropic/claude-code

# Create Claude Code workspace for TWIC project
echo "📁 Setting up Claude Code workspace..."
mkdir -p ~/claude-workspace/twic-processing
cd ~/claude-workspace/twic-processing

# Initialize Claude Code configuration
cat > .claude-code.json << 'EOF'
{
  "workspaceRoot": "/root/claude-workspace/twic-processing",
  "defaultShell": "/bin/bash",
  "environment": {
    "PYTHONPATH": "/root/chessmind-twic",
    "TWIC_PROJECT_ROOT": "/root/chessmind-twic"
  },
  "aliases": {
    "twic": "cd ~/chessmind-twic && source venv/bin/activate",
    "monitor": "~/chessmind-twic/scripts/monitor/system_status.sh",
    "logs": "tail -f ~/chessmind-twic/logs/*.log"
  }
}
EOF

# Create symbolic links to TWIC project
ln -s ~/chessmind-twic ~/claude-workspace/twic-processing/chessmind-twic

# Setup firewall for Claude Code (if needed)
echo "🔥 Configuring firewall..."
ufw allow 22    # SSH
ufw allow 8080  # Claude Code web interface (if applicable)
ufw --force enable

echo "✅ Claude Code setup complete!"
echo ""
echo "📋 Usage Instructions:"
echo "1. Start Claude Code: claude-code"
echo "2. Access workspace: ~/claude-workspace/twic-processing"
echo "3. TWIC project linked at: ~/claude-workspace/twic-processing/chessmind-twic"
echo ""
echo "🔧 Useful Commands in Claude Code:"
echo "- Use 'twic' alias to navigate to project and activate Python env"
echo "- Use 'monitor' to check system status"
echo "- Use 'logs' to monitor download progress"
echo ""
echo "🎯 Ready for TWIC processing with Claude Code!"