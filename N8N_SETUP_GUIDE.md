# BE FORWARD Scraper - n8n Integration Setup Guide

This guide shows you how to host your modular scraper script and integrate it with n8n for daily automation and Facebook posting.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Hosting Options](#hosting-options)
3. [Setup on Your Server](#setup-on-your-server)
4. [n8n Integration](#n8n-integration)
5. [Data Storage and Retrieval](#data-storage-and-retrieval)
6. [Security Considerations](#security-considerations)

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                        n8n (Cloud or Self-Hosted)                  │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐   │
│  │  Daily Cron │ ──▶ │ HTTP Request │ ──▶ │ Your Server API    │   │
│  │  (9:00 AM)  │    │ (POST /scrape)│    │ (Port 5000)        │   │
│  └─────────────┘    └──────────────┘    └──────────┬─────────┘   │
│                                                  │               │
│  ┌─────────────┐    ┌──────────────┐            ▼               │
│  │   Poll      │ ──▶ │ HTTP Request │ ───▶ ┌─────────────┐      │
│  │ (Every min) │    │ (/webhook/)   │      │ Your Script │      │
│  └─────────────┘    └──────────────┘      │             │      │
│                                            │ Scrape BE   │      │
│  ┌─────────────────────────────────────┐  │ FORWARD     │      │
│  │  Facebook Page                      │  │             │      │
│  │  (Upload images + post)             │  └─────────────┘      │
│  └─────────────────────────────────────┘         │             │
└──────────────────────────────────────────────────┼─────────────┘
                                                   │
                                                   ▼
                                    ┌─────────────────────────┐
                                    │  Local Storage           │
                                    │  ├── output/vehicles/    │
                                    │  │   ├── CB123456/       │
                                    │  │   │   ├── data.json    │
                                    │  │   │   ├── facebook.json│
                                    │  │   │   └── images/      │
                                    │  │   └── CB789012/       │
                                    │  └── state/              │
                                    └─────────────────────────┘
```

---

## Hosting Options

### Option 1: VPS/Cloud Server (Recommended)

**Pros:**
- Always online, accessible from anywhere
- Dedicated resources
- Can host multiple services
- Easy to scale

**Recommended Providers:**
- **DigitalOcean** - $6/month (1GB RAM)
- **Linode** - $5/month (1GB RAM)
- **Hetzner** - €4/month (2GB RAM)
- **Vultr** - $6/month (1GB RAM)

### Option 2: Home Server

**Pros:**
- Free (if you have spare hardware)
- Complete control
- No monthly costs

**Cons:**
- Need port forwarding/DDNS
- Power consumption
- Reliability depends on your internet

### Option 3: Docker Container (Portable)

**Pros:**
- Easy deployment
- Consistent environment
- Can run anywhere Docker is available

---

## Setup on Your Server

### Step 1: Prepare the Server

```bash
# SSH into your server
ssh user@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv git

# Install nginx (optional, for reverse proxy)
sudo apt install -y nginx
```

### Step 2: Deploy Your Script Files

```bash
# Option A: Copy from local machine
scp -r beforwardScarping user@your-server-ip:/home/user/

# Option B: Clone from git (if you have it in a repo)
git clone https://github.com/yourusername/beforward-scraper.git
cd beforward-scraper

# Navigate to project directory
cd /home/user/beforwardScarping

# Create virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure the API Server

```bash
# Edit the API server if needed
nano api_server.py

# Test the API server manually
python3 api_server.py

# In another terminal, test it
curl http://localhost:5000/health
# Should return: {"status":"healthy",...}
```

### Step 4: Create systemd Service

```bash
# Copy the service file
sudo cp beforward-api.service /etc/systemd/system/

# Edit the service file with your paths
sudo nano /etc/systemd/system/beforward-api.service

# Replace:
# - YOUR_USERNAME with your username
# - /path/to/beforwardScarping with actual path

# Example:
# User=proximalink
# WorkingDirectory=/home/proximalink/beforwardScarping
# ExecStart=/usr/bin/python3 /home/proximalink/beforwardScarping/api_server.py
# StandardOutput=append:/home/proximalink/beforwardScarping/state/api.log
# StandardError=append:/home/proximalink/beforwardScarping/state/api_error.log

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable beforward-api
sudo systemctl start beforward-api

# Check status
sudo systemctl status beforward-api

# View logs
sudo journalctl -u beforward-api -f
```

### Step 5: Configure Firewall (if enabled)

```bash
# Allow port 5000
sudo ufw allow 5000

# Or use nginx reverse proxy (recommended for production)
sudo nano /etc/nginx/sites-available/beforward-api
```

Add nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/beforward-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL (optional but recommended)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## n8n Integration

### Option A: n8n Cloud (Easiest)

1. Sign up at https://n8n.io/cloud
2. Create a new workflow
3. Import the workflow JSON files from `n8n/` directory
4. Replace `YOUR_SERVER_IP` with your actual server IP/domain
5. Activate the workflow

### Option B: Self-Hosted n8n

```bash
# Install n8n using npm
npm install -g n8n

# Or using Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Or install as service
sudo nano /etc/systemd/system/n8n.service
```

Add to n8n.service:

```ini
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME
ExecStart=/usr/local/bin/n8n start
Restart=always
RestartSec=10
Environment=WEBHOOK_URL=https://your-n8n-domain.com/

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable n8n
sudo systemctl start n8n
```

### n8n Workflow Setup

1. **Daily Scraper Trigger** (`n8n/daily-scraper-trigger.json`)
   - Triggers every day at 9 AM
   - Calls `POST /scrape` endpoint
   - Logs success/failure

2. **Fetch & Post to Facebook** (`n8n/fetch-and-post-facebook.json`)
   - Polls `/webhook/new-vehicle` every minute
   - Gets latest vehicle not yet posted
   - Formats Facebook post
   - Posts to Facebook Page

### API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/scrape` | POST | Trigger daily scraper |
| `/scrape/force` | POST | Force scrape (skip daily check) |
| `/vehicle/latest` | GET | Get latest scraped vehicle |
| `/vehicle/all` | GET | Get all vehicles (limit=10) |
| `/vehicle/<ref_no>` | GET | Get vehicle by reference number |
| `/images/<ref_no>` | GET | Get list of images for vehicle |
| `/image/<ref_no>/<filename>` | GET | Download specific image |
| `/webhook/new-vehicle` | POST | Get next unposted vehicle |

---

## Data Storage and Retrieval

### File Structure

```
beforwardScarping/
├── output/
│   └── vehicles/
│       ├── 2024_TOYOTA_CB454801/
│       │   ├── data.json          # All vehicle specs
│       │   ├── facebook.json      # Facebook post template
│       │   ├── metadata.txt       # Scraping timestamp
│       │   └── images/            # Downloaded images (cropped)
│       │       ├── 001.jpg
│       │       ├── 002.jpg
│       │       └── ...
│       ├── 2019_TOYOTA_CB779329/
│       └── ...
└── state/
    ├── scraper_state.json         # Tracks scraped vehicles
    ├── posted_vehicles.json       # Tracks vehicles posted to FB
    ├── api.log                    # API server logs
    └── api_error.log              # API error logs
```

### Accessing Data in n8n

**Method 1: HTTP API (Recommended)**

```javascript
// In n8n HTTP Request node
GET http://YOUR_SERVER_IP:5000/vehicle/latest

// Returns:
{
  "title": "Used 2019 TOYOTA HILUX...",
  "ref_no": "CB779329",
  "specs": {
    "mileage": "42,244 km",
    "engine_size": "2,500cc",
    ...
  },
  "price": "$15,200",
  "images": [
    "/path/to/vehicles/.../images/001.jpg",
    "/path/to/vehicles/.../images/002.jpg"
  ],
  "facebook_post": {
    "headline": "🚗 FOR SALE: ...",
    "body": "...",
    "hashtags": [...]
  }
}
```

**Method 2: Direct File Access (if n8n on same server)**

```javascript
// Use n8n's Read Binary Files node
// Path: /home/user/beforwardScarping/output/vehicles/
// Then parse JSON with Code node
```

### Image Access for Facebook Posting

**Option 1: Public URL (with nginx)**

Configure nginx to serve images:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # API endpoints
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Static image files
    location /images/ {
        alias /home/user/beforwardScarping/output/vehicles/;
        autoindex off;
        add_header Cache-Control "public, max-age=31536000";
    }
}
```

Then in n8n, use URLs like:
```
https://your-domain.com/images/2019_TOYOTA_CB779329/images/001.jpg
```

**Option 2: Upload from local path**

Use n8n's Facebook node with local file paths:
```javascript
// Format paths for Facebook node
{{ $json.images.map(img => `/home/user/beforwardScarping/${img}`) }}
```

---

## Security Considerations

### 1. API Authentication (Recommended)

Add to `api_server.py`:

```python
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

users = {
    "n8n": "your_secure_password_here"
}

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username
    return False

# Protect endpoints
@app.route("/scrape", methods=["POST"])
@auth.login_required
def scrape():
    # ... existing code
```

Then in n8n HTTP Request node:
- Enable Authentication
- Type: Basic Auth
- Username: `n8n`
- Password: `your_secure_password_here`

### 2. API Key (Alternative)

```python
# Add to api_server.py
API_KEY = os.environ.get("API_KEY", "your-secret-api-key")

def check_api_key():
    api_key = request.headers.get("X-API-Key")
    return api_key == API_KEY

@app.before_request
def authenticate():
    if request.path == "/health":
        return
    if not check_api_key():
        return jsonify({"error": "Unauthorized"}), 401
```

In n8n, add header:
```
X-API-Key: your-secret-api-key
```

### 3. Firewall Rules

```bash
# Only allow n8n cloud IP (if using cloud)
sudo ufw allow from 1.2.3.4 to any port 5000

# Or use VPN
```

### 4. Rate Limiting

```python
# Add to api_server.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)

@app.route("/scrape", methods=["POST"])
@limiter.limit("1 per hour")
def scrape():
    # ... existing code
```

---

## Testing the Setup

### 1. Test API Server

```bash
# Health check
curl http://localhost:5000/health

# Trigger scraper
curl -X POST http://localhost:5000/scrape \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Get latest vehicle
curl http://localhost:5000/vehicle/latest

# Get images list
curl http://localhost:5000/images/CB779329
```

### 2. Test n8n Workflows

1. Import the workflow JSON into n8n
2. Replace `YOUR_SERVER_IP` with actual IP/domain
3. Execute the workflow manually
4. Check execution logs
5. Verify Facebook post (if configured)

### 3. Monitor Logs

```bash
# API server logs
tail -f state/api.log

# Systemd service logs
sudo journalctl -u beforward-api -f

# Scraper logs
tail -f state/scraper.log
```

---

## Troubleshooting

### Issue: API server not accessible from n8n cloud

**Solution:**
- Check firewall: `sudo ufw status`
- Check if service is running: `sudo systemctl status beforward-api`
- Check logs: `sudo journalctl -u beforward-api -n 50`
- Verify port is open: `netstat -tulpn | grep 5000`

### Issue: Images not posting to Facebook

**Solution:**
- Check if images are accessible at the URLs
- For local files, ensure n8n has file system access
- Check Facebook API permissions
- Try posting single image first to test

### Issue: Scraper runs but no data returned

**Solution:**
- Check if `output/vehicles/` has data
- Check `state/scraper_state.json`
- Verify scraper ran successfully: check logs
- Test scraper manually: `python3 daily_scraper.py --force`

---

## Backup Strategy

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/user/backups/beforward"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup output and state
tar -czf $BACKUP_DIR/beforward_$DATE.tar.gz \
  /home/user/beforwardScarping/output \
  /home/user/beforwardScarping/state

# Keep last 30 days
find $BACKUP_DIR -name "beforward_*.tar.gz" -mtime +30 -delete

echo "Backup completed: beforward_$DATE.tar.gz"
EOF

chmod +x backup.sh

# Add to cron
crontab -e
# Add: 0 2 * * * /home/user/backup.sh
```

---

## Summary

| Component | Purpose | Location |
|-----------|---------|----------|
| `api_server.py` | HTTP API for n8n communication | Your server |
| `daily_scraper.py` | Main scraping logic | Your server |
| `output/vehicles/` | Scraped vehicle data | Your server filesystem |
| `state/` | State tracking files | Your server filesystem |
| n8n Cloud/Self-hosted | Workflow automation | n8n |
| Facebook Page | Final posting destination | Facebook |

**Data Flow:**
1. n8n triggers scraper daily at 9 AM
2. Scraper saves data to local filesystem
3. n8n polls webhook for new vehicles
4. n8n formats Facebook post
5. n8n posts to Facebook with images

**All files are hosted on your server** - the modular structure stays intact. n8n only communicates via HTTP API and retrieves data as needed.
