# Free Setup Guide - Render + n8n

## Can I Run Both on Render Free?

**YES!** Render allows multiple free services.

But there's a **catch:**
- ❌ Free services spin down after **15 minutes of inactivity**
- ⚠️ Cold start takes ~30 seconds
- ⚠️ Not reliable for 24/7 automation

---

## What is the API Key?

The API key is simply a **password** to protect your scraper API.

### Why do you need it?

**Without API key:**
```
Anyone can call: https://your-api.onrender.com/scrape
And use up your resources!
```

**With API key:**
```
Only you (with the key) can call the API
```

### How to set it?

You can set it to **anything you want** - it's just a random string:

```
API_KEY=my-super-secret-key-12345
API_KEY=beforward-2024-secure-key
API_KEY=abc123xyz789
```

### How to use it?

When calling the API, include the key in the header:

```bash
curl -X POST https://your-api.onrender.com/scrape \
  -H "X-API-Key: my-super-secret-key-12345" \
  -d '{"force": true}'
```

**If key is wrong or missing → 401 Unauthorized**

---

## Free Setup Options

### Option 1: Scraper on Render + n8n Local Docker (Testing)

**Cost:** $0
**Best for:** Testing and development

```
┌─────────────────────┐      ┌─────────────────┐
│  Render (Free)      │      │  Your PC        │
│  beforward-api      │─────▶│  n8n Docker     │
│  (Always on*)       │      │  (When PC on)   │
└─────────────────────┘      └─────────────────┘
     *Spins down after 15min
```

**Setup:**

1. Deploy scraper to Render (from your GitHub repo)

2. Run n8n locally:
```bash
docker run -d --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=admin123 \
  -v n8n_data:/home/node/.n8n \
  docker.io/n8nio/n8n:latest
```

3. In n8n (http://localhost:5678), create workflow:
   - HTTP Request → `https://beforward-scraper-api.onrender.com/scrape`
   - Add Header → `X-API-Key: your-key`

**Limitation:** Your PC must be on for n8n to trigger the scraper

---

### Option 2: Both on Render Free (Full Cloud)

**Cost:** $0
**Best for:** Fully cloud-based (with spin-down limitation)

```
┌─────────────────────────────────────┐
│  Render (Free)                      │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ beforward    │  │ n8n         │ │
│  │ scraper      │──▶│ Docker      │ │
│  └──────────────┘  └─────────────┘ │
│        ↓                ↓            │
│   Spins down      Spins down        │
│   after 15min     after 15min       │
└─────────────────────────────────────┘
```

**Setup:**

**Service 1: Scraper API**
1. Go to Render → New Web Service
2. Connect repo: `Pakheria/beforward-scraper`
3. Runtime: Docker
4. Add env vars:
   ```
   API_KEY=your-secret-key-here
   DEFAULT_COUNTRY=uae
   ```
5. Deploy → Get URL: `https://beforward-scraper-api.onrender.com`

**Service 2: n8n**
1. Go to Render → New Web Service
2. Choose "Existing Image" or Public Docker
3. Image: `n8nio/n8n:latest`
4. Add env vars:
   ```
   N8N_BASIC_AUTH_ACTIVE=true
   N8N_BASIC_AUTH_USER=admin
   N8N_BASIC_AUTH_PASSWORD=your-password
   WEBHOOK_URL=https://your-n8n.onrender.com
   ```
5. Deploy → Get URL: `https://your-n8n.onrender.com`

**Limitation:** Both services spin down after 15min, but n8n's scheduler will wake them up!

---

### Option 3: Use Railway for n8n (Better Free Tier)

**Cost:** $5 one-time credit, then free
**Best for:** 24/7 n8n without spin-down

```
┌───────────────────┐      ┌─────────────────────┐
│  Render (Free)    │      │  Railway (Free)     │
│  beforward-api    │─────▶│  n8n (24/7)         │
│  (Spins down)     │      │  (Always on!)       │
└───────────────────┘      └─────────────────────┘
```

**Why Railway?**
- ✅ $5 one-time credit for new users
- ✅ Services stay running (don't spin down)
- ✅ Perfect for n8n

**Setup:**

1. **Scraper on Render** (same as Option 2)

2. **n8n on Railway:**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from Docker Image"
   - Image: `n8nio/n8n:latest`
   - Add env vars (same as Render)
   - Deploy → Get 24/7 n8n URL!

---

## Quick Start - Recommended Free Setup

### For Testing (Option 1)

```bash
# 1. Deploy scraper to Render (done from your repo)
# 2. Run n8n locally
docker run -d --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=admin123 \
  -v n8n_data:/home/node/.n8n \
  docker.io/n8nio/n8n:latest

# 3. Access n8n at http://localhost:5678
# 4. Create workflow with HTTP Request to your Render API
```

### For Production Free Tier (Option 2 - Both Render)

**Deploy scraper + n8n both on Render**

They will spin down but n8n's scheduler will wake them up at the scheduled time.

---

## API Key Summary

| Question | Answer |
|----------|--------|
| **What is it?** | A password to protect your API |
| **Can I set anything?** | YES! Any random string |
| **Is it required?** | No, but highly recommended |
| **How to use?** | Add `X-API-Key: your-key` header |
| **Example keys:** | `my-secret-key-123`, `beforward-2024`, `abc-xyz-789` |

**Set in Render:**
```
Environment Variables → Add Variable
Name: API_KEY
Value: my-super-secret-key-here
```

**Use in n8n:**
```
HTTP Request Node → Authentication → Header Auth
Name: X-API-Key
Value: my-super-secret-key-here
```

---

## Comparison

| Setup | Cost | Reliability | PC Required? |
|-------|------|-------------|--------------|
| **Render + Local n8n** | Free | ⭐⭐⭐ | Yes (when running) |
| **Both on Render** | Free | ⭐⭐⭐ | No |
| **Render + Railway** | Free* | ⭐⭐⭐⭐⭐ | No |
| **Render + n8n Cloud** | ~$30-40/mo | ⭐⭐⭐⭐⭐ | No |

*Railway gives $5 one-time credit for new users

---

## My Recommendation

**For testing:** Use **Option 1** (Render + Local n8n Docker)

**For production free:** Use **Option 2** (Both on Render) - accept 15min spin-down

**For 24/7 free:** Use **Option 3** (Render + Railway) - best of both worlds!

---

## Next Steps

Which option do you want to try? I can help you set it up!

1. **Option 1** - I'll help with local n8n Docker setup
2. **Option 2** - I'll create the n8n Render deployment guide
3. **Option 3** - I'll create the Railway deployment guide
