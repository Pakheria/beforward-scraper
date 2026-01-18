# Oracle Cloud Free Tier Setup - 24/7 Automation

Complete guide for deploying BE FORWARD scraper + n8n on Oracle Cloud's Always Free tier.

## Why Oracle Cloud Free Tier?

| Feature | Oracle Cloud | Render | Railway |
|---------|--------------|--------|---------|
| **Cost** | **FREE forever** | Free | Free ($5 credit) |
| **Always ON** | ✅ Yes | ❌ Spins down | ❌ After credit |
| **RAM** | **1-24 GB** | 512 MB | 512 MB |
| **CPU** | **1-4 OCPU** | Shared | Shared |
| **Storage** | **200 GB** | Ephemeral | 1 GB |

**You get:**
- ✅ 2 AMD VMs (1 OCPU, 1GB RAM) - Always Free
- ✅ 4 ARM VMs (up to 24GB RAM!) - Always Free
- ✅ 200 GB storage
- ✅ 10 TB/month outbound transfer
- ✅ No spin-down, runs 24/7

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Oracle Cloud Free Tier VM                  │
│  ┌──────────────────┐  ┌─────────────────┐ │
│  │ beforward-api    │  │ n8n             │ │
│  │ (Flask/Gunicorn) │  │ (Docker)        │ │
│  │ Port 5000        │  │ Port 5678       │ │
│  └──────────────────┘  └─────────────────┘ │
│         │                     │             │
│         └──────────┬──────────┘             │
│                    │                        │
│            ┌───────▼────────┐              │
│            │  nginx (Proxy) │              │
│            │  Port 80/443   │              │
│            └────────────────┘              │
│                                              │
│  🌐 Public IP: 123.45.67.89                 │
│  📁 Storage: 200GB                          │
│  💾 RAM: 1GB (AMD) or 24GB (ARM)           │
└─────────────────────────────────────────────┘
```

---

## Prerequisites

1. **Oracle Cloud Account** - https://www.oracle.com/cloud/free/
2. **Credit Card** (required for verification, but NOT charged)
3. **SSH Client** - Already on your system

---

## Step 1: Create Oracle Cloud Account

1. Go to https://www.oracle.com/cloud/free/
2. Click **"Try for Free"**
3. Create account (requires email + phone verification)
4. Add credit card for verification (NOT charged)
5. Choose your home region (closest to you)

---

## Step 2: Create Free Tier VM

### 2.1 Access Console

1. After signup, go to Oracle Cloud Console: https://cloud.oracle.com
2. Sign in with your credentials

### 2.2 Create Instance

1. Click **"汉堡 menu"** (☰) → **"Compute"** → **"Instances"**
2. Click **"Create Instance"**
3. Configure:

   **Name:** `beforward-scraper`

   **Compartment:** (Leave default)

   **Placement:**
   - Availability Domain: Any
   - Capacity Type: **Always Free**

   **Shape:**
   - Select **"VM.Standard.E2.1.Micro"** (Always Free)
   - 1 OCPU, 1 GB RAM
   - **OR** choose ARM Ampere A1 for more RAM (up to 24GB!)

   **Networking:**
   - Virtual Cloud Network: Create new VCN
   - Subnet: Create new subnet
   - **Assign Public IP:** ✅ CHECK THIS!
   - **Boot Volume:** 50 GB (Always Free)

   **SSH Key:**
   - Click **"Save Private Key"** to download your private key
   - Save as `oracle-key.pem`

4. Click **"Create Instance"**

5. Wait 3-5 minutes for provisioning

### 2.3 Get Your VM Details

1. Your instance will show in the list
2. Note down:
   - **Public IP Address** (e.g., 129.123.45.67)
   - **Username** (usually `ubuntu` or `opc`)

---

## Step 3: Connect to Your VM

### 3.1 Set Up SSH Key

```bash
# Move the downloaded key and secure it
mv ~/Downloads/oracle-key.pem ~/.ssh/
chmod 600 ~/.ssh/oracle-key.pem

# Add to SSH config
cat >> ~/.ssh/config << 'EOF'
Host oracle
    HostName YOUR_PUBLIC_IP
    User ubuntu
    IdentityFile ~/.ssh/oracle-key.pem
    StrictHostKeyChecking no
EOF
```

Replace `YOUR_PUBLIC_IP` with your actual IP.

### 3.2 SSH Into VM

```bash
ssh oracle
```

You should now be connected to your Oracle VM!

---

## Step 4: Prepare VM

### 4.1 Update System

```bash
# Run these commands on your Oracle VM
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx
```

### 4.2 Create Project Directory

```bash
# Clone your repo
cd ~
git clone https://github.com/Pakheria/beforward-scraper.git
cd beforward-scraper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 4.3 Create Output Directories

```bash
mkdir -p output/vehicles state
```

---

## Step 5: Run Scraper API

### 5.1 Test API Server

```bash
# Test run in foreground (to see any errors)
source .venv/bin/activate
python api_server.py
```

Press Ctrl+C to stop. If you see "Running on http://0.0.0.0:5000", it's working!

### 5.2 Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/beforward-api.service
```

Paste this content:

```ini
[Unit]
Description=BE FORWARD Scraper API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/beforward-scraper
Environment="PATH=/home/ubuntu/beforward-scraper/.venv/bin"
ExecStart=/home/ubuntu/beforward-scraper/.venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    api_server:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save: Ctrl+O, Enter, Ctrl+X

### 5.3 Start Service

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable beforward-api
sudo systemctl start beforward-api

# Check status
sudo systemctl status beforward-api

# View logs
sudo journalctl -u beforward-api -f
```

### 5.4 Test API

```bash
# On your VM
curl http://localhost:5000/health

# Should return:
# {"status":"healthy","timestamp":"..."}
```

---

## Step 6: Install n8n

### 6.1 Install Docker

```bash
# Run these commands on your Oracle VM
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker ubuntu

# Log out and back in, or run:
newgrp docker
```

### 6.2 Run n8n Container

```bash
# Create n8n data directory
mkdir -p ~/n8n_data

# Run n8n
docker run -d \
  --name n8n \
  --restart unless-stopped \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=your-secure-password-here \
  -e N8N_HOST=0.0.0.0 \
  -e N8N_PORT=5678 \
  -e WEBHOOK_URL=https://your-domain-or-ip.com \
  -e GENERIC_TIMEZONE=UTC \
  -e TZ=UTC \
  -v ~/n8n_data:/home/node/.n8n \
  n8nio/n8n:latest
```

### 6.3 Test n8n

```bash
# Check container is running
docker ps

# Check n8n logs
docker logs n8n
```

---

## Step 7: Set Up nginx Reverse Proxy (Optional but Recommended)

This allows you to:
- Use HTTPS (SSL)
- Access both services on port 80/443
- Have clean URLs

### 7.1 Configure nginx

```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/beforward
```

Paste this content:

```nginx
# HTTP redirect to HTTPS (add later)
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # For API
    location /api/ {
        proxy_pass http://localhost:5000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # For n8n
    location /n8n/ {
        proxy_pass http://localhost:5678/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Replace `YOUR_DOMAIN_OR_IP` with your actual domain or IP.

### 7.2 Enable Site

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/beforward /etc/nginx/sites-enabled/

# Test nginx
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 7.3 Access Services

Now you can access:
- **API:** `http://YOUR_IP/api/`
- **n8n:** `http://YOUR_IP/n8n/`

---

## Step 8: Configure Firewall

```bash
# Oracle Cloud has external firewall, configure in console

# But also configure UFW on VM
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Check status
sudo ufw status
```

---

## Step 9: Configure Oracle Cloud Firewall

### 9.1 Access Security Lists

1. In Oracle Console, go to **Networking** → **Virtual Cloud Networks**
2. Click your VCN
3. Click **"Security Lists"** in left sidebar
4. Click your security list

### 9.2 Add Ingress Rules

Click **"Add Ingress Rules"** and add:

| Source | CIDR | Destination Port | Protocol | Description |
|--------|------|------------------|----------|-------------|
| 0.0.0.0/0 | - | 22 | TCP | SSH |
| 0.0.0.0/0 | - | 80 | TCP | HTTP |
| 0.0.0.0/0 | - | 443 | TCP | HTTPS |

---

## Step 10: Set Up SSL Certificate (Optional but Recommended)

### 10.1 Get Domain (Optional)

If you have a domain, point it to your Oracle VM IP.

### 10.2 Install SSL with Certbot

```bash
# If you have a domain:
sudo certbot --nginx -d your-domain.com

# If using IP only (self-signed cert):
sudo apt install -y ssl-cert
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx.key \
    -out /etc/nginx/ssl/nginx.crt
```

---

## Step 11: Connect n8n to Scraper API

### 11.1 Access n8n

Open in browser:
```
http://YOUR_VM_PUBLIC_IP:5678
```

Login with:
- Username: `admin`
- Password: `your-secure-password-here`

### 11.2 Create Workflow

1. Click **"Add workflow"**

2. Add **Schedule Trigger**:
   - Set daily time (e.g., 9:00 AM)

3. Add **HTTP Request**:
   ```
   Method: POST
   URL: http://localhost:5000/scrape
   Body: {"force": false}
   ```

4. Add destination (Slack, Email, etc.)

5. **Save** and **Activate**

---

## Step 12: Test Everything

### 12.1 Test API

```bash
# On your local machine
curl http://YOUR_VM_IP:5000/health

# Or via nginx
curl http://YOUR_VM_IP/api/health
```

### 12.2 Test n8n

1. Open n8n in browser
2. Execute workflow manually
3. Check if scraper runs

### 12.3 Check Logs

```bash
# API logs
sudo journalctl -u beforward-api -f

# n8n logs
docker logs n8n -f

# nginx logs
sudo tail -f /var/log/nginx/access.log
```

---

## Oracle Cloud Free Tier Limits

| Resource | Always Free Limit |
|----------|-------------------|
| **Compute** | 2 AMD VMs (1 OCPU, 1GB RAM) OR 4 ARM VMs (up to 24GB RAM) |
| **Storage** | 200 GB (Boot volumes) |
| **Bandwidth** | 10 TB/month outbound |
| **Load Balancers** | Not included (use nginx) |

**Recommendation:** Use ARM Ampere A1 for more RAM!

---

## Maintenance

### Update Code

```bash
# SSH into VM
ssh oracle

cd ~/beforward-scraper
git pull
source .venv/bin/activate
pip install -r requirements.txt

# Restart API
sudo systemctl restart beforward-api
```

### Update n8n

```bash
docker stop n8n
docker rm n8n
docker pull n8nio/n8n:latest

# Run n8n command again (from Step 6.2)
```

### Monitor Resources

```bash
# Check CPU/RAM usage
htop

# Check disk usage
df -h

# Check docker
docker stats
```

---

## Backup Strategy

```bash
# Create backup script
cat > ~/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup n8n data
tar -czf $BACKUP_DIR/n8n_$DATE.tar.gz ~/n8n_data

# Backup scraper output
tar -czf $BACKUP_DIR/scraper_$DATE.tar.gz ~/beforward-scraper/output

# Keep last 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x ~/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * ~/backup.sh
```

---

## URLs After Setup

| Service | URL | Notes |
|---------|-----|-------|
| **Scraper API** | `http://YOUR_IP:5000` | Direct access |
| **Scraper API** | `http://YOUR_IP/api/` | Via nginx |
| **n8n Dashboard** | `http://YOUR_IP:5678` | Direct access |
| **n8n Dashboard** | `http://YOUR_IP/n8n/` | Via nginx |
| **Health Check** | `http://YOUR_IP/api/health` | API status |

---

## Troubleshooting

### Issue: Can't SSH into VM

**Solution:**
1. Check Oracle Cloud firewall (Security List)
2. Check VM is running in Console
3. Verify you're using correct SSH key

### Issue: API not accessible from browser

**Solution:**
1. Check Oracle Cloud firewall allows port 5000
2. Check service is running: `sudo systemctl status beforward-api`
3. Check logs: `sudo journalctl -u beforward-api`

### Issue: n8n container won't start

**Solution:**
1. Check Docker is running: `docker ps`
2. Check logs: `docker logs n8n`
3. Restart: `docker restart n8n`

### Issue: Out of memory

**Solution:**
1. Switch to ARM Ampere A1 (up to 24GB RAM!)
2. Or add more VMs (you get 4 ARM VMs free)

---

## Cost

| Item | Cost |
|------|------|
| **VM (Always Free)** | $0 |
| **Storage (200GB)** | $0 |
| **Bandwidth (10TB)** | $0 |
| **TOTAL** | **$0/month forever** |

---

## Next Steps

1. ✅ Create Oracle Cloud account
2. ✅ Create Always Free VM
3. ✅ SSH into VM
4. ✅ Deploy scraper + n8n
5. ✅ Configure n8n workflow
6. ✅ Enjoy 24/7 free automation!

---

## Summary

You now have:
- ✅ Scraper API running 24/7
- ✅ n8n running 24/7
- ✅ Daily automation setup
- ✅ No monthly costs
- ✅ No spin-down issues

**All on Oracle Cloud Free Tier!**
