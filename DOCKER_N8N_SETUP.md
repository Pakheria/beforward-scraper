# BE FORWARD Scraper - Docker & Render Deployment Guide

Complete guide for deploying the scraper API on Render and integrating with n8n Docker container.

## Table of Contents

1. [Quick Start - Local Testing](#quick-start---local-testing)
2. [Deploy to Render](#deploy-to-render)
3. [n8n Integration](#n8n-integration)
4. [Environment Variables](#environment-variables)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start - Local Testing

### Step 1: Test Locally with Docker Compose

```bash
# 1. Navigate to project directory
cd beforwardScarping

# 2. Start both services (scraper API + n8n)
docker-compose up -d

# 3. Check services are running
docker-compose ps

# 4. View logs
docker-compose logs -f

# 5. Test the API
curl http://localhost:5000/health
curl http://localhost:5000/vehicle/latest

# 6. Access n8n
open http://localhost:5678
# Default credentials:
# Username: admin
# Password: your-secure-password-here
```

### Step 2: Test n8n Workflow

1. Open n8n at `http://localhost:5678`
2. Create a new workflow
3. Add **HTTP Request** node:
   - Method: `POST`
   - URL: `http://beforward-api:5000/scrape`
   - Body: `{"force": true, "skip_images": false}`
4. Execute the workflow
5. You should see vehicle data returned

---

## Deploy to Render

### Step 1: Prepare Your Files

**Required files to upload:**
```
beforwardScarping/
├── Dockerfile                  # ✅ Required
├── render.yaml                 # ✅ Required
├── requirements.txt            # ✅ Required
├── .dockerignore               # ✅ Recommended
├── api_server.py               # ✅ Required
├── daily_scraper.py            # ✅ Required
├── config.py                   # ✅ Required
└── utils/                      # ✅ Required
    ├── __init__.py
    ├── scraper.py
    ├── parser.py
    ├── downloader.py
    ├── image_processor.py
    └── facebook_formatter.py
```

### Step 2: Push to GitHub

```bash
# Initialize git if not already done
git init

# Create .gitignore
cat > .gitignore << 'EOF'
.venv/
__pycache__/
*.pyc
output/
state/
*.log
.DS_Store
EOF

# Add all files
git add .

# Commit
git commit -m "Add BE FORWARD scraper with Docker support"

# Create repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/beforward-scraper.git
git branch -M main
git push -u origin main
```

### Step 3: Deploy on Render

1. **Sign up/Login to Render** - https://render.com

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select `beforward-scraper` repo

3. **Configure the Service**

   **Basic Settings:**
   - Name: `beforward-scraper-api`
   - Region: Oregon (or closest to you)
   - Branch: `main`
   - Runtime: `Docker`
   - **Build & Deploy** will read from `Dockerfile`

   **Environment Variables** (see full list below):
   ```
   PORT=5000
   LOG_LEVEL=INFO
   DEFAULT_COUNTRY=uae
   ENABLE_CROPPING=true
   API_KEY=your-random-secret-key
   ```

   **Advanced Settings:**
   - **Disk**: Add persistent disk
     - Name: `data`
     - Mount Path: `/app/output`
     - Size: 1 GB (free tier) or 10 GB (paid)

4. **Deploy!**

   Render will:
   - Build the Docker image
   - Start the container
   - Assign a URL like: `https://beforward-scraper-api.onrender.com`

5. **Get Your Service URL**

   After deployment, Render will show:
   ```
   Service URL: https://beforward-scraper-api.onrender.com
   ```

6. **Test Your Deployed API**

   ```bash
   # Health check
   curl https://beforward-scraper-api.onrender.com/health

   # Get latest vehicle
   curl https://beforward-scraper-api.onrender.com/vehicle/latest

   # Trigger scraper (add API key if configured)
   curl -X POST https://beforward-scraper-api.onrender.com/scrape \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-random-secret-key" \
     -d '{"force": true}'
   ```

---

## n8n Integration

### Option 1: n8n Cloud (Easiest)

1. **Sign up for n8n Cloud** - https://n8n.io/cloud

2. **Create Workflow for Daily Scraping**

   **Node 1: Schedule Trigger**
   - Type: Schedule Trigger
   - Cron Expression: `0 9 * * *` (daily at 9 AM)

   **Node 2: HTTP Request**
   - Method: POST
   - URL: `https://beforward-scraper-api.onrender.com/scrape`
   - Authentication: None (or Header API Key)
   - Send Headers: `X-API-Key: your-random-secret-key`
   - Send Body: Yes
   - Body Type: JSON
   - JSON Body:
     ```json
     {
       "force": false
     }
     ```

   **Node 3: Set** (Extract vehicle data)
   - Mode: Automatic
   - Assignments:
     - `ref_no`: `{{ $json.vehicle.specs.ref_no }}`
     - `title`: `{{ $json.vehicle.title }}`
     - `price`: `{{ $json.vehicle.price }}`

   **Node 4: Facebook** (or any other destination)
   - Configure Facebook node with extracted data

3. **Activate Workflow**

### Option 2: Self-Hosted n8n (Docker)

If you're running n8n in Docker locally or on a VPS:

```bash
# Using the docker-compose.yml provided
docker-compose up -d

# Access n8n at http://localhost:5678
```

**Important**: When n8n is in Docker and your scraper is on Render:

- Use Render's URL: `https://beforward-scraper-api.onrender.com`
- NOT `http://beforward-api:5000` (that only works in same Docker network)

**If both are on same VPS**, update docker-compose.yml:

```yaml
# In n8n service, add:
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Then use `http://host.docker.internal:5000` from n8n.

---

## Environment Variables

### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Port for API server (Render sets this automatically) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_COUNTRY` | `uae` | Default country to scrape |
| `CURRENT_COUNTRY` | `uae` | Override current country |
| `ENABLE_CROPPING` | `true` | Enable/disable image cropping |
| `CROP_PERCENTAGE` | `7` | Percentage to crop from bottom |
| `CROP_QUALITY` | `95` | JPEG quality (85-100) |
| `API_KEY` | - | API key for authentication (recommended!) |
| `N8N_WEBHOOK_URL` | - | n8n webhook for notifications |

### Setting Environment Variables

**On Render Dashboard:**
1. Go to your service
2. Click "Environment" tab
3. Add each variable

**Or in render.yaml:**
```yaml
envVars:
  - key: API_KEY
    generateValue: true  # Render generates secure value
```

**Or locally (.env file):**
```bash
# Create .env file
cat > .env << 'EOF'
PORT=5000
LOG_LEVEL=INFO
DEFAULT_COUNTRY=uae
ENABLE_CROPPING=true
CROP_PERCENTAGE=7
CROP_QUALITY=95
API_KEY=your-secret-key-here
EOF

# Update docker-compose.yml to use .env:
# env_file:
#   - .env
```

---

## n8n Workflow Examples

### Example 1: Daily Scraping + Post to Slack

```
[Schedule Trigger] → [HTTP Request: /scrape] → [Slack: Post Message]
      (9:00 AM)             (Render API)         (Vehicle data)
```

**HTTP Request Node:**
```json
{
  "method": "POST",
  "url": "https://beforward-scraper-api.onrender.com/scrape",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "headerAuth": {
    "name": "X-API-Key",
    "value": "your-api-key"
  },
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "{\n  \"force\": false\n}"
}
```

**Slack Node:**
```javascript
// In Slack node text:
New vehicle scraped!

Ref: {{ $json.vehicle.specs.ref_no }}
Title: {{ $json.vehicle.title }}
Price: {{ $json.vehicle.price }}
Location: {{ $json.vehicle.specs.location }}

{{ $json.vehicle.facebook_post.post_content.headline }}
```

### Example 2: Poll for New Vehicles

```
[Poll Trigger] → [HTTP Request: /webhook/new-vehicle] → [IF: New?] → [Facebook Post]
  (Every 5m)              (Get unposted)               (Post if new)
```

**Webhook Response:**
```json
{
  "vehicle": { ... },
  "post_required": true
}
```

### Example 3: Manual Trigger with Parameters

```
[Manual Trigger] → [Set] → [HTTP Request: /scrape] → [Format] → [Post]
                      |          (with params)            (Facebook)
                      v
                  Select country,
                  skip images, etc.
```

---

## Data Persistence

### Render Disk Storage

Render's free tier does NOT include persistent disk. Your scraped data will be lost on redeploy.

**Solutions:**

1. **Upgrade to Paid** ($7/month starter includes 10GB disk)

2. **Use External Storage** (Recommended for production)

   Update `config.py` to use S3 or similar:
   ```python
   # Instead of local paths
   S3_BUCKET = "beforward-vehicles"
   AWS_REGION = "us-east-1"
   ```

3. **Accept Data Loss** (if using webhook pattern)
   - scraper runs → immediately posts to n8n
   - n8n stores data in its own database
   - scraper output is temporary

### Disk Configuration on Render

1. Go to your service → "Advanced"
2. Add Disk:
   - Name: `data`
   - Mount Path: `/app/output`
   - Size: `10` (GB)

---

## Security

### 1. Enable API Key Authentication

Update `api_server.py` to require API key:

```python
from functools import wraps

API_KEY = os.environ.get("API_KEY")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Apply to protected routes:
@app.route("/scrape", methods=["POST"])
@require_api_key
def scrape():
    # ... existing code
```

### 2. Use HTTPS

Render provides SSL automatically. Always use `https://` URLs.

### 3. Rate Limiting

Add to `requirements.txt`:
```
flask-limiter>=3.5.0
```

Add to `api_server.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)

@app.route("/scrape", methods=["POST"])
@limiter.limit("10 per hour")
@require_api_key
def scrape():
    # ... existing code
```

---

## Troubleshooting

### Issue: Container crashes on Render

**Check logs:**
```bash
# In Render dashboard, view logs
# Common issues:
# - Out of memory (upgrade plan)
# - Missing dependencies (check requirements.txt)
# - Port not set (Render sets PORT env var)
```

### Issue: Scraping times out

**Solution:**
1. Increase timeout in `api_server.py`:
   ```python
   result = subprocess.run(cmd, timeout=300)  # 5 minutes
   ```

2. Or use async pattern:
   - n8n triggers scrape
   - API returns immediately with "started"
   - n8n polls `/webhook/status` for completion

### Issue: n8n can't reach API

**Check:**
1. Is API deployed? Test URL in browser
2. Is API key correct?
3. Is CORS enabled? (Yes, in `api_server.py`)
4. Are you using `http://` instead of `https://`?

### Issue: Images not accessible

**Problem:** Images are saved to `/app/output/vehicles/...` but n8n can't access them.

**Solutions:**
1. **Serve images via API** (already implemented)
   ```
   GET /image/<ref_no>/<filename>
   ```

2. **Use public URL with nginx** (advanced)
   - Add nginx reverse proxy
   - Serve images from `/output/`

3. **Upload to cloud storage** (production)
   - Use S3, Cloudinary, or similar
   - n8n uploads images to Facebook from URLs

---

## Quick Reference

### Render URLs

Once deployed, you'll have:
```
Service URL: https://your-service.onrender.com
Health:      https://your-service.onrender.com/health
Scrape:      https://your-service.onrender.com/scrape
Latest:      https://your-service.onrender.com/vehicle/latest
```

### n8n HTTP Request Configuration

```
Method: POST
URL: https://your-service.onrender.com/scrape
Headers:
  X-API-Key: your-api-key
  Content-Type: application/json
Body:
  {"force": true, "skip_images": false}
```

### Local Testing

```bash
# Start everything
docker-compose up -d

# Test API
curl http://localhost:5000/health

# Access n8n
open http://localhost:5678

# View logs
docker-compose logs -f beforward-api

# Stop everything
docker-compose down
```

---

## Next Steps

1. **Deploy to Render** using this guide
2. **Test the API** with curl/Postman
3. **Create n8n workflow** with HTTP Request node
4. **Set up daily trigger** in n8n
5. **Configure Facebook posting** (or other destination)
6. **Monitor logs** in Render dashboard

---

## File Checklist for Upload

✅ **Required Files:**
- [x] `Dockerfile`
- [x] `render.yaml`
- [x] `requirements.txt`
- [x] `.dockerignore`
- [x] `api_server.py`
- [x] `daily_scraper.py`
- [x] `config.py`
- [x] `utils/__init__.py`
- [x] `utils/scraper.py`
- [x] `utils/parser.py`
- [x] `utils/downloader.py`
- [x] `utils/image_processor.py`
- [x] `utils/facebook_formatter.py`

❌ **Do NOT Upload:**
- `.venv/` (virtual environment)
- `output/` (will be created in container)
- `state/` (will be created in container)
- `*.log` files
- `.git/` (git creates this)
- `__pycache__/` (Python cache)

---

## Support

If you encounter issues:

1. Check Render logs in dashboard
2. Test locally with `docker-compose`
3. Verify environment variables
4. Check API health endpoint
5. Review this guide's troubleshooting section
