#!/bin/bash
# BE FORWARD Scraper - Oracle Cloud Free Tier Setup Script
# Run this on your Oracle Cloud VM after SSH-ing in

set -e

echo "=========================================="
echo "BE FORWARD Scraper - Oracle VM Setup"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run as normal user, not root${NC}"
    exit 1
fi

# Update system
echo -e "${YELLOW}➜ Updating system...${NC}"
sudo apt update && sudo apt upgrade -y

# Install required packages
echo -e "${YELLOW}➜ Installing required packages...${NC}"
sudo apt install -y python3 python3-pip python3-venv git nginx curl

# Install Docker
echo -e "${YELLOW}➜ Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Clone repository
echo -e "${YELLOW}➜ Cloning repository...${NC}"
if [ ! -d "beforward-scraper" ]; then
    git clone https://github.com/Pakheria/beforward-scraper.git
    cd beforward-scraper
else
    cd beforward-scraper
    git pull
fi

# Create virtual environment
echo -e "${YELLOW}➜ Setting up Python environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Create directories
echo -e "${YELLOW}➜ Creating directories...${NC}"
mkdir -p output/vehicles state

# Create systemd service for API
echo -e "${YELLOW}➜ Creating systemd service...${NC}"
sudo tee /etc/systemd/system/beforward-api.service > /dev/null <<EOF
[Unit]
Description=BE FORWARD Scraper API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/.venv/bin"
ExecStart=$(pwd)/.venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    api_server:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable beforward-api
sudo systemctl start beforward-api

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet beforward-api; then
    echo -e "${GREEN}✓ API service started successfully${NC}"
else
    echo -e "${RED}✗ API service failed to start${NC}"
    echo "Check logs: sudo journalctl -u beforward-api -n 50"
    exit 1
fi

# Install n8n with Docker
echo -e "${YELLOW}➜ Installing n8n with Docker...${NC}"
mkdir -p ~/n8n_data

# Check if n8n container already exists
if docker ps -a | grep -q n8n; then
    echo "n8n container already exists, removing..."
    docker stop n8n 2>/dev/null || true
    docker rm n8n 2>/dev/null || true
fi

# Run n8n container
docker run -d \
    --name n8n \
    --restart unless-stopped \
    -p 5678:5678 \
    -e N8N_BASIC_AUTH_ACTIVE=true \
    -e N8N_BASIC_AUTH_USER=admin \
    -e N8N_BASIC_AUTH_PASSWORD=admin123 \
    -e N8N_HOST=0.0.0.0 \
    -e N8N_PORT=5678 \
    -e GENERIC_TIMEZONE=UTC \
    -e TZ=UTC \
    -v ~/n8n_data:/home/node/.n8n \
    n8nio/n8n:latest

# Wait for n8n to start
sleep 5

# Check n8n is running
if docker ps | grep -q n8n; then
    echo -e "${GREEN}✓ n8n container started successfully${NC}"
else
    echo -e "${RED}✗ n8n container failed to start${NC}"
    echo "Check logs: docker logs n8n"
    exit 1
fi

# Configure UFW firewall
echo -e "${YELLOW}➜ Configuring firewall...${NC}"
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 5000/tcp  # API
sudo ufw allow 5678/tcp  # n8n
echo "y" | sudo ufw enable

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me)

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}Services are running:${NC}"
echo ""
echo "1. BE FORWARD Scraper API:"
echo "   - Local: http://localhost:5000"
echo "   - Health: http://localhost:5000/health"
echo "   - Public: http://$PUBLIC_IP:5000"
echo ""
echo "2. n8n Dashboard:"
echo "   - Local: http://localhost:5678"
echo "   - Public: http://$PUBLIC_IP:5678"
echo "   - Username: admin"
echo "   - Password: admin123"
echo ""
echo "3. Service Management:"
echo "   - API status: sudo systemctl status beforward-api"
echo "   - API logs: sudo journalctl -u beforward-api -f"
echo "   - n8n logs: docker logs n8n -f"
echo ""
echo "4. Next Steps:"
echo "   a) Open n8n in browser: http://$PUBLIC_IP:5678"
echo "   b) Login with admin/admin123"
echo "   c) Create workflow with HTTP Request node"
echo "   d) URL: http://localhost:5000/scrape"
echo "   e) Body: {\"force\": false}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Configure Oracle Cloud Security List${NC}"
echo "   Go to Oracle Console → Networking → Security Lists"
echo "   Add ingress rules for ports: 22, 80, 443, 5000, 5678"
echo ""
echo -e "${YELLOW}⚠️  SECURITY: Change default n8n password!${NC}"
echo "   docker stop n8n"
echo "   docker rm n8n"
echo "   Run the docker run command with new password"
echo ""
