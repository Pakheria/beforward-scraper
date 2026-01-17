#!/bin/bash
# BE FORWARD Scraper - API Server Setup Script
# Run this on your server to set up the API server for n8n integration

set -e

echo "=========================================="
echo "BE FORWARD Scraper - API Server Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Detect project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_info "Project directory: $PROJECT_DIR"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install it first."
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install it first."
    exit 1
fi
print_success "pip3 found"

# Install/upgrade dependencies
print_info "Installing Python dependencies..."
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
pip install -q --upgrade pip
pip install -q -r requirements.txt
print_success "Dependencies installed"

# Create state directory if it doesn't exist
mkdir -p "$PROJECT_DIR/state"
print_success "State directory created"

# Create systemd service file
print_info "Creating systemd service..."

# Get current username
USER=$(whoami)
# Get absolute path
PROJECT_ABS_PATH=$(realpath "$PROJECT_DIR")

cat > /tmp/beforward-api.service << EOF
[Unit]
Description=BE FORWARD Scraper API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ABS_PATH
ExecStart=$PROJECT_ABS_PATH/.venv/bin/python $PROJECT_ABS_PATH/api_server.py
Restart=always
RestartSec=10
Environment=PORT=5000

# Logging
StandardOutput=append:$PROJECT_ABS_PATH/state/api.log
StandardError=append:$PROJECT_ABS_PATH/state/api_error.log

[Install]
WantedBy=multi-user.target
EOF

# Copy to systemd directory
sudo cp /tmp/beforward-api.service /etc/systemd/system/
print_success "Systemd service file created"

# Reload systemd
sudo systemctl daemon-reload
print_success "Systemd reloaded"

# Enable service
print_info "Enabling beforward-api service..."
sudo systemctl enable beforward-api
print_success "Service enabled"

# Start service
print_info "Starting beforward-api service..."
sudo systemctl start beforward-api
print_success "Service started"

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl is-active --quiet beforward-api; then
    print_success "API server is running!"
else
    print_error "API server failed to start. Check logs with: sudo journalctl -u beforward-api -n 50"
    exit 1
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}API Server is running at:${NC}"
echo "  http://localhost:5000"
echo "  http://$SERVER_IP:5000"
echo ""
echo "Available endpoints:"
echo "  GET  /health              - Health check"
echo "  POST /scrape              - Trigger scraper"
echo "  POST /scrape/force        - Force scrape"
echo "  GET  /vehicle/latest      - Get latest vehicle"
echo "  GET  /vehicle/all         - Get all vehicles"
echo "  GET  /vehicle/<ref_no>    - Get vehicle by ref"
echo "  GET  /images/<ref_no>     - Get images list"
echo "  GET  /image/<ref_no>/<fn> - Download image"
echo ""
echo "Test commands:"
echo "  curl http://localhost:5000/health"
echo "  curl http://localhost:5000/vehicle/latest"
echo ""
echo "Service management:"
echo "  sudo systemctl status beforward-api"
echo "  sudo systemctl stop beforward-api"
echo "  sudo systemctl restart beforward-api"
echo "  sudo journalctl -u beforward-api -f"
echo ""
echo "For n8n integration, use: http://$SERVER_IP:5000"
echo ""
echo "Next steps:"
echo "  1. Test the API: curl http://localhost:5000/health"
echo "  2. Set up nginx reverse proxy (optional but recommended)"
echo "  3. Configure n8n workflows with your server IP"
echo "  4. Check logs: tail -f state/api.log"
echo ""
