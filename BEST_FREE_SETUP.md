# Best Free Setup - Render + Railway

Complete guide for 24/7 automation without spending money!

## Architecture

```
┌─────────────────────────────┐      ┌──────────────────────────┐
│  Render (Free)              │      │  Railway (Free)           │
│  ┌─────────────────────┐    │      │  ┌─────────────────────┐ │
│  │ beforward-scraper   │ ──┼─────▶│  │ n8n (24/7 running)  │ │
│  │ Spins down 15min    │    │      │  │ Always ON!          │ │
│  └─────────────────────┘    │      │  └─────────────────────┘ │
└─────────────────────────────┘      └──────────────────────────┘
            │                                  │
            │                                  │
            ▼                                  ▼
    BE FORWARD Website                   Facebook/Slack/etc
```

**Why this works:**
- ✅ n8n on Railway stays running 24/7 (no spin-down!)
- ✅ n8n's scheduler can wake up the scraper when needed
- ✅ Both free tiers
- ✅ No local PC needed

---

## Step 1: Deploy Scraper to Render

Your repo is ready: `https://github.com/Pakheria/beforward-scraper`

### 1.1 Create Render Account

1. Go to https://render.com
2. Sign up (GitHub OAuth)
3. You get free credits automatically

### 1.2 Deploy Web Service

1. Click **"New +"** → **"Web Service"**
2. **Connect GitHub** → Authorize Render
3. Select **`beforward-scraper`** repo
4. Configure:

   | Field | Value |
   |-------|-------|
   | Name | `beforward-scraper-api` |
   | Runtime | **Docker** |
   | Branch | `master` |
   | Region | Oregon (or nearest) |

5. **Add Environment Variables** (click "Advanced" → "Add Environment Variable"):

   ```
   API_KEY=my-super-secret-key-123
   DEFAULT_COUNTRY=uae
   ENABLE_CROPPING=true
   ```

6. Click **"Deploy Web Service"**

7. Wait for deployment (~5 minutes)
8. You'll get a URL like: `https://beforward-scraper-api.onrender.com`

### 1.3 Test the API

```bash
# Health check
curl https://beforward-scraper-api.onrender.com/health

# Should return:
# {"status":"healthy","timestamp":"...","output_dir":"..."}
```

---

## Step 2: Deploy n8n to Railway

### 2.1 Create Railway Account

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Sign up with GitHub
4. You get **$5 one-time credit** (plenty for testing!)

### 2.2 Deploy n8n

#### Option A: Quick Deploy from Docker Image (Easiest)

1. In Railway dashboard, click **"New Project"** → **"Deploy from Docker Image"**

2. Enter Docker image:
   ```
   n8nio/n8n:latest
   ```

3. Click **"Deploy"**

4. Once deployed, click on your project → **"Variables"** tab

5. Add these environment variables:

   | Key | Value |
   |-----|-------|
   | `N8N_BASIC_AUTH_ACTIVE` | `true` |
   | `N8N_BASIC_AUTH_USER` | `admin` |
   | `N8N_BASIC_AUTH_PASSWORD` | `your-secure-password` |
   | `WEBHOOK_URL` | (Railway auto-fills this) |
   | `N8N_HOST` | `0.0.0.0` |
   | `N8N_PORT` | `5678` |

6. Click **"Restart Deployment"** (top right)

#### Option B: Deploy from GitHub (Alternative)

If you prefer to deploy from your repo:

1. Push `railway.toml` to your GitHub repo (already in your repo!)

2. In Railway, click **"New Project"** → **"Deploy from GitHub Repo"**

3. Select `beforward-scraper` repo

4. Railway will detect `railway.toml` and deploy

### 2.3 Get Your n8n URL

After deployment, Railway gives you a URL like:
```
https://your-project-name.up.railway.app
```

### 2.4 Access n8n

1. Open your n8n URL in browser
2. Login with:
   - Username: `admin`
   - Password: `your-secure-password`

3. You should see the n8n workflow editor!

---

## Step 3: Connect n8n to Render API

Now let's create a workflow in n8n that calls your Render scraper.

### 3.1 Create Your First Workflow

1. In n8n, click **"Add workflow"**

2. Click **"Add trigger"** → Search for **"Schedule Trigger"**

3. Configure Schedule:
   - Click "Schedule" → "Cron Expression"
   - Enter: `0 9 * * *` (daily at 9 AM UTC)
   - Or click "UI" and set time

4. Click **"+"** to add node → Search for **"HTTP Request"**

5. Configure HTTP Request:
   ```
   Method: POST
   URL: https://beforward-scraper-api.onrender.com/scrape

   Authentication:
   → Select "Header Auth"
   → Name: X-API-Key
   → Value: my-super-secret-key-123

   Body:
   → Send Body: Yes
   → Body Type: JSON
   → JSON Body: {"force": false}
   ```

6. Click **"Test"** to run it once

7. You should see vehicle data returned!

### 3.2 Add More Nodes

Let's format the data and post it somewhere:

**Add "Set" node to extract vehicle info:**
1. Click **"+"** → **"Set"**
2. Add assignments:
   ```
   ref_no: {{ $json.vehicle.specs.ref_no }}
   title: {{ $json.vehicle.title }}
   price: {{ $json.vehicle.price }}
   mileage: {{ $json.vehicle.specs.mileage }}
   location: {{ $json.vehicle.specs.location }}
   ```

**Add "Slack" or "Email" node:**
1. Click **"+"** → Search for "Slack" or "Gmail"
2. Configure with your credentials
3. Use the extracted data in the message

### 3.3 Save and Activate

1. Click **"Save"** (top right)
2. Toggle **"Active"** to ON
3. Your workflow will now run daily at 9 AM!

---

## Step 4: Test the Complete Flow

### 4.1 Manual Test

1. In n8n, click **"Execute Workflow"**
2. Check the output of each node
3. Verify you get vehicle data

### 4.2 Test API Directly

```bash
# Test scraper API
curl -X POST https://beforward-scraper-api.onrender.com/scrape \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-super-secret-key-123" \
  -d '{"force": true, "skip_images": true}'
```

### 4.3 Check n8n Logs

1. In n8n, click **"Executions"** (left sidebar)
2. See all workflow runs
3. Click on any run to see detailed logs

---

## Important Notes

### About Railway Free Tier

✅ **What you get:**
- $5 one-time credit ( lasts ~1-2 months of light usage)
- Service stays running 24/7
- No spin-down
- 512MB RAM
- Shared CPU

⚠️ **After credit expires:**
- Service pauses after ~5 hours of inactivity per month
- But for daily scraping, you'll be fine!

💡 **To extend free usage:**
- Connect a credit card (Railway gives $5/month free)
- Or use the $5 credit wisely

### About Render Free Tier

✅ **What you get:**
- Free forever
- 512MB RAM
- Shared CPU

⚠️ **Limitations:**
- Spins down after 15 minutes of inactivity
- Cold start takes ~30 seconds

💡 **Why this works:**
- n8n wakes it up when calling the API
- Cold start is acceptable for daily scraping

---

## URLs You'll Have

After setup, you'll have these URLs:

| Service | URL Example | Purpose |
|---------|-------------|---------|
| **Scraper API** | `https://beforward-scraper-api.onrender.com` | API endpoints |
| **n8n Dashboard** | `https://your-project.up.railway.app` | Workflow editor |
| **API Health** | `...onrender.com/health` | Check if scraper is running |
| **Latest Vehicle** | `...onrender.com/vehicle/latest` | Get latest data |

---

## Troubleshooting

### Issue: n8n can't reach Render API

**Check:**
1. Is Render service deployed? (Check Render dashboard)
2. Is API key correct?
3. Is URL correct? (https not http)
4. Test API in browser:
   ```
   https://beforward-scraper-api.onrender.com/health
   ```

### Issue: Railway service won't start

**Check:**
1. Environment variables are set correctly
2. No typos in variable names
3. Click "Restart Deployment" in Railway dashboard

### Issue: Scraper times out

**Solution:**
1. Reduce image count (use `skip_images: true` for testing)
2. Or upgrade to paid tier for more RAM

---

## Monthly Cost Estimate

| Service | Free Tier | Paid if Needed |
|---------|-----------|----------------|
| Render (scraper) | Free forever | $7/month (Starter) |
| Railway (n8n) | $5 one-time credit | $5/month after credit |

**Total to start: FREE**
**Total ongoing: $0-5/month**

---

## Next Steps

1. ✅ **Deploy scraper to Render** (repo ready!)
2. ✅ **Deploy n8n to Railway** (follow guide above)
3. ✅ **Create workflow in n8n** (connect to Render API)
4. ✅ **Test and activate** (daily automation!)

---

## Quick Reference

**Render Dashboard:** https://dashboard.render.com
**Railway Dashboard:** https://railway.app/dashboard

**API Endpoints:**
```
Health:    /health
Scrape:    /scrape (POST)
Latest:    /vehicle/latest
All:       /vehicle/all
Images:    /images/<ref_no>
Download:  /image/<ref_no>/<filename>
```

**n8n Workflow:**
```
[Schedule] → [HTTP Request] → [Set] → [Slack/Email/Facebook]
   (9AM)      (Render API)      (extract)    (post somewhere)
```

---

Need help with any step? Let me know!
