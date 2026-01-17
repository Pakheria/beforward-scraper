# Quick Deploy Guide - Render + n8n Docker

## Files Created for You

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds container image for Render |
| `render.yaml` | Render deployment configuration |
| `.dockerignore` | Excludes unnecessary files from image |
| `docker-compose.yml` | Local testing with n8n |
| `DOCKER_N8N_SETUP.md` | Full deployment documentation |

---

## Environment Variables

### Set These in Render Dashboard:

| Variable | Value | Required |
|----------|-------|----------|
| `PORT` | `5000` | ✅ Yes (auto-set) |
| `LOG_LEVEL` | `INFO` | Optional |
| `DEFAULT_COUNTRY` | `uae` | Optional |
| `ENABLE_CROPPING` | `true` | Optional |
| `CROP_PERCENTAGE` | `7` | Optional |
| `CROP_QUALITY` | `95` | Optional |
| `API_KEY` | `generate-random-key` | Recommended |

---

## Deploy to Render (5 Steps)

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Add Docker scraper for Render"
git remote add origin https://github.com/YOUR_USERNAME/beforward-scraper.git
git push -u origin main
```

### 2. Create Web Service on Render
- Go to https://render.com
- Click "New +" → "Web Service"
- Connect your GitHub repo
- Select `beforward-scraper`

### 3. Configure Service
| Setting | Value |
|---------|-------|
| Name | `beforward-scraper-api` |
| Runtime | Docker |
| Region | Oregon (or nearest) |
| Branch | main |

### 4. Add Environment Variables
In Render Dashboard → Environment → Add:
```
API_KEY=your-random-secure-key-here
DEFAULT_COUNTRY=uae
ENABLE_CROPPING=true
```

### 5. Deploy & Get URL
Render will give you:
```
https://your-service-name.onrender.com
```

---

## Test Deployed API

```bash
# Health check
curl https://your-service.onrender.com/health

# Get latest vehicle
curl https://your-service.onrender.com/vehicle/latest

# Trigger scraper (with API key)
curl -X POST https://your-service.onrender.com/scrape \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"force": true}'
```

---

## n8n Workflow Setup

### If using n8n Docker (docker.io/n8nio/n8n:latest)

#### Start n8n:
```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=your-password \
  -e WEBHOOK_URL=https://your-n8n-domain.com \
  -v n8n_data:/home/node/.n8n \
  docker.io/n8nio/n8n:latest
```

#### Access n8n:
```
http://localhost:5678
Username: admin
Password: your-password
```

### Create Workflow in n8n:

**Node 1: Schedule Trigger**
- Cron: `0 9 * * *` (daily at 9 AM)

**Node 2: HTTP Request**
- Method: `POST`
- URL: `https://your-service.onrender.com/scrape`
- Authentication → Header Auth:
  - Name: `X-API-Key`
  - Value: `your-api-key`
- Body → JSON:
  ```json
  {"force": false}
  ```

**Node 3: Slack/Facebook/Email**
- Use data from Node 2
- `{{ $json.vehicle.title }}`
- `{{ $json.vehicle.price }}`
- `{{ $json.vehicle.specs.mileage }}`

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check if API is running |
| `/scrape` | POST | Trigger daily scraper |
| `/vehicle/latest` | GET | Get most recent vehicle |
| `/vehicle/all` | GET | Get all vehicles (limit=10) |
| `/vehicle/<ref_no>` | GET | Get specific vehicle |
| `/images/<ref_no>` | GET | List images for vehicle |
| `/image/<ref_no>/<file>` | GET | Download image |
| `/webhook/new-vehicle` | POST | Get next unposted vehicle |

---

## Local Testing with Docker Compose

```bash
# Start both scraper API and n8n
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove all data
docker-compose down -v
```

---

## Important Notes

### Render Free Tier Limitations:
- ⚠️ **No persistent disk** - data lost on redeploy
- ⚠️ **512MB RAM** - may timeout during scraping
- ⚠️ **Spins down after 15min inactivity** - cold start ~30s

**Recommendations:**
1. Use webhook pattern (immediately post to n8n)
2. Or upgrade to Starter plan ($7/mo) for disk + always-on

### Image Access:
- Images are served via API: `/image/<ref_no>/<filename>`
- For Facebook posting, n8n can:
  - Download from API URLs
  - Or use public CDN (advanced setup)

### Security:
- Set `API_KEY` environment variable
- Use HTTPS only (Render provides SSL)
- Consider rate limiting for production

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Container crashes | Check Render logs, verify dependencies |
| Scraping timeouts | Upgrade to paid plan for more RAM |
| n8n can't connect | Verify URL, check API key, test in browser |
| Images not accessible | Use `/image/` endpoint, not direct file paths |
| Data lost on redeploy | Add persistent disk (paid) or use webhook pattern |

---

## File Structure for Upload

```
beforward-scraper/
├── Dockerfile                 ← Required
├── render.yaml                ← Required
├── requirements.txt           ← Required
├── .dockerignore              ← Recommended
├── api_server.py              ← Required
├── daily_scraper.py           ← Required
├── config.py                  ← Required
├── utils/
│   ├── __init__.py
│   ├── scraper.py
│   ├── parser.py
│   ├── downloader.py
│   ├── image_processor.py
│   └── facebook_formatter.py
└── DOCKER_N8N_SETUP.md        ← Documentation
```

**DO NOT upload:**
- `.venv/`
- `output/`
- `state/`
- `__pycache__/`
- `*.log` files

---

## Full Documentation

See `DOCKER_N8N_SETUP.md` for complete guide with:
- Detailed troubleshooting
- n8n workflow examples
- Security hardening
- S3/Cloud storage integration
- Advanced configurations
