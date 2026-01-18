#!/bin/bash
# BE FORWARD Scraper - Oracle Cloud ARM VM Setup Script
# For Oracle Linux 9 (ARM) with 6GB RAM
# Run this on your Oracle Cloud ARM VM after SSH-ing in

set -e

echo "=========================================="
echo "BE FORWARD Scraper - Oracle Linux 9 ARM Setup"
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
    echo "Run: sudo su - opc -c 'bash oracle-setup-arm.sh'"
    exit 1
fi

# Update system (using dnf for Oracle Linux 9)
echo -e "${YELLOW}➜ Updating system...${NC}"
sudo dnf update -y

# Install required packages
echo -e "${YELLOW}➜ Installing required packages...${NC}"
sudo dnf install -y python3 python3-pip python3-devel git nginx curl

# Install Docker
echo -e "${YELLOW}➜ Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    # Add Docker repository for Oracle Linux
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf install -y docker-ce docker-ce-cli containerd.io
    sudo systemctl enable docker
    sudo systemctl start docker
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
SERVICE_FILE="/etc/systemd/system/beforward-api.service"
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=BE FORWARD Scraper API
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/.venv/bin:/usr/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$(pwd)/.venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
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
    -e EXECUTIONS_PROCESS=main \
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

# Configure firewalld (Oracle Linux uses firewalld, not ufw)
echo -e "${YELLOW}➜ Configuring firewall...${NC}"
# Check if firewalld is running
if systemctl is-active --quiet firewalld; then
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --permanent --add-port=5000/tcp
    sudo firewall-cmd --permanent --add-port=5678/tcp
    sudo firewall-cmd --reload
    echo -e "${GREEN}✓ Firewall configured (firewalld)${NC}"
else
    # Start firewalld if not running
    sudo systemctl start firewalld
    sudo systemctl enable firewalld
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --permanent --add-port=5000/tcp
    sudo firewall-cmd --permanent --add-port=5678/tcp
    sudo firewall-cmd --reload
    echo -e "${GREEN}✓ Firewall configured (firewalld)${NC}"
fi

# Configure SELinux (Oracle Linux has SELinux enabled by default)
echo -e "${YELLOW}➜ Configuring SELinux...${NC}
# Allow nginx to connect to backend
if command -v setsebool &> /dev/null; then
    sudo setsebool -P httpd_can_network_connect 1
    echo -e "${GREEN}✓ SELinux configured${NC}"
fi

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
echo "   - Health Check: http://localhost:5000/health"
echo "   - Public URL: http://$PUBLIC_IP:5000"
echo "   - API Root: http://$PUBLIC_IP:5000/"
echo ""
echo "2. n8n Dashboard:"
echo "   - Public URL: http://$PUBLIC_IP:5678"
echo "   - Username: admin"
echo "   - Password: admin123"
echo ""
echo "3. Service Management:"
echo "   - API status: sudo systemctl status beforward-api"
echo "   - API restart: sudo systemctl restart beforward-api"
echo "   - API logs: sudo journalctl -u beforward-api -f"
echo "   - n8n logs: docker logs n8n -f"
echo "   - n8n restart: docker restart n8n"
echo ""
echo "4. Oracle Linux 9 Notes:"
echo "   - Package manager: dnf (or yum)"
echo "   - Firewall: firewalld (not ufw)"
echo "   - SELinux: Enabled (permissive mode)"
echo "   - User: opc (not ubuntu)"
echo ""
echo "5. Next Steps:"
echo "   a) Open n8n: http://$PUBLIC_IP:5678"
echo "   b) Login: admin / admin123"
echo "   c) Create workflow → HTTP Request →"
echo "      URL: http://localhost:5000/scrape"
echo "      Body: {\"force\": false}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Configure Oracle Cloud Security List${NC}"
echo "   Go to Oracle Console → Networking → Security Lists"
echo "   Add ingress rules for ports: 22, 80, 443, 5000, 5678"
echo ""
echo -e "${YELLOW}⚠️  SECURITY: Change default n8n password!${NC}"
echo "   docker stop n8n && docker rm n8n"
echo "   Then run docker run with new password"
echo ""
echo -e "${GREEN}✓ Setup complete! Your ARM VM has 6GB RAM!${NC}"
echo ""
