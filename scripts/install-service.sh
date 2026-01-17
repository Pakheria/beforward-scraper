#!/bin/bash
###############################################################################
# BE FORWARD Daily Scraper - Service Installation Script
#
# This script installs the daily scraper as a systemd service that runs
# automatically every day.
#
# Usage:
#   sudo ./install-service.sh          # Install service
#   sudo ./install-service.sh --remove # Remove service
#   sudo ./install-service.sh --status # Check service status
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration from config.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-beforward-daily}"
SERVICE_DESCRIPTION="${SERVICE_DESCRIPTION:-BE FORWARD Daily Vehicle Scraper}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
SCRAPER_SCRIPT="${SCRAPER_SCRIPT:-$SCRIPT_DIR/daily_scraper.py}"

# systemd paths
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
TIMER_FILE="/etc/systemd/system/$SERVICE_NAME.timer"

###############################################################################
# Functions
###############################################################################

print_header() {
    echo ""
    echo "============================================"
    echo "$1"
    echo "============================================"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    # Verify scraper script exists
    if [[ ! -f "$SCRAPER_SCRIPT" ]]; then
        print_error "Scraper script not found: $SCRAPER_SCRIPT"
        exit 1
    fi

    print_success "Python 3 found: $(python3 --version)"
    print_success "Scraper script found: $SCRAPER_SCRIPT"
}

install_service() {
    print_header "Installing BE FORWARD Daily Scraper Service"

    check_root
    check_python

    # Create service file
    print_success "Creating systemd service file..."

    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=$SERVICE_DESCRIPTION
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$SUDO_USER
Group=$SUDO_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_BIN $SCRAPER_SCRIPT
StandardOutput=append:$SCRIPT_DIR/state/service.log
StandardError=append:$SCRIPT_DIR/state/service.log

# Run even if user is not logged in
RemainAfterExit=yes

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    print_success "Created: $SERVICE_FILE"

    # Create timer file (runs daily at 9:00 AM)
    print_success "Creating systemd timer file..."

    cat > "$TIMER_FILE" << EOF
[Unit]
Description=$SERVICE_DESCRIPTION Timer
Requires=$SERVICE_NAME.service

[Timer]
# Run daily at 9:00 AM
OnCalendar=*-*-* 09:00:00
# Also run 15 minutes after boot (if missed)
OnBootSec=15min
# If system was off at scheduled time, run immediately on next boot
Persistent=true

[Install]
WantedBy=timers.target
EOF

    print_success "Created: $TIMER_FILE"

    # Create state directory
    mkdir -p "$SCRIPT_DIR/state"
    chown $SUDO_USER:$SUDO_USER "$SCRIPT_DIR/state"

    # Reload systemd
    print_success "Reloading systemd daemon..."
    systemctl daemon-reload

    # Enable and start timer
    print_success "Enabling service timer..."
    systemctl enable "$SERVICE_NAME.timer"

    print_success "Starting service timer..."
    systemctl start "$SERVICE_NAME.timer"

    # Show status
    echo ""
    echo "Service installed successfully!"
    echo ""
    echo "Service files:"
    echo "  - $SERVICE_FILE"
    echo "  - $TIMER_FILE"
    echo ""
    echo "Log file:"
    echo "  - $SCRIPT_DIR/state/service.log"
    echo ""
    echo "Next scheduled run: $(systemctl list-timers '$SERVICE_NAME.timer' --no-pager | tail -n 1 | awk '{print $1, $2, $3, $4}')"
    echo ""
    echo "Useful commands:"
    echo "  sudo systemctl status $SERVICE_NAME.timer"
    echo "  sudo systemctl start $SERVICE_NAME.service  # Run now"
    echo "  sudo systemctl stop $SERVICE_NAME.timer     # Stop automatic runs"
    echo "  sudo journalctl -u $SERVICE_NAME -f        # View logs"
    echo ""
}

remove_service() {
    print_header "Removing BE FORWARD Daily Scraper Service"

    check_root

    # Stop and disable
    if systemctl is-active --quiet "$SERVICE_NAME.timer" 2>/dev/null; then
        print_success "Stopping timer..."
        systemctl stop "$SERVICE_NAME.timer"
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME.timer" 2>/dev/null; then
        print_success "Disabling timer..."
        systemctl disable "$SERVICE_NAME.timer"
    fi

    # Remove files
    if [[ -f "$SERVICE_FILE" ]]; then
        print_success "Removing service file..."
        rm -f "$SERVICE_FILE"
    fi

    if [[ -f "$TIMER_FILE" ]]; then
        print_success "Removing timer file..."
        rm -f "$TIMER_FILE"
    fi

    # Reload systemd
    print_success "Reloading systemd daemon..."
    systemctl daemon-reload

    # Reset failed units
    systemctl reset-failed 2>/dev/null || true

    print_success "Service removed successfully!"
}

show_status() {
    print_header "BE FORWARD Daily Scraper Service Status"

    # Check if installed
    if [[ ! -f "$SERVICE_FILE" ]]; then
        print_warning "Service is not installed"
        echo ""
        echo "Run: sudo ./install-service.sh"
        exit 0
    fi

    # Timer status
    echo "Timer Status:"
    systemctl status "$SERVICE_NAME.timer" --no-pager
    echo ""

    # Last run info
    echo "Next scheduled runs:"
    systemctl list-timers "$SERVICE_NAME.timer" --no-pager
    echo ""

    # Service logs (last 20 lines)
    echo "Recent logs:"
    if [[ -f "$SCRIPT_DIR/state/service.log" ]]; then
        tail -n 20 "$SCRIPT_DIR/state/service.log"
    else
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    fi
}

###############################################################################
# Main
###############################################################################

# Parse arguments
case "${1:-install}" in
    install)
        install_service
        ;;
    remove|uninstall)
        remove_service
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 [install|remove|status]"
        echo ""
        echo "Commands:"
        echo "  install   Install the systemd service (default)"
        echo "  remove    Remove the systemd service"
        echo "  status    Show service status"
        exit 1
        ;;
esac
