# Setup Guide

Complete setup instructions for Agent Transponder.

---

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database (Neon free tier recommended)
- Accounts with API access:
  - [Fathom](https://fathom.video) (free)
  - [HubSpot](https://hubspot.com) (free CRM)
  - [Groq](https://console.groq.com) (free tier)
  - [Resend](https://resend.com) (free tier)

---

## Step 1: Database Setup (Neon)

1. Go to [neon.tech](https://neon.tech) and create a free account
2. Create a new project
3. Copy the connection string (format: `postgresql://user:pass@host/db?sslmode=require`)
4. Save this for your `.env` file

---

## Step 2: Fathom Setup

### Get API Key & Create Webhook

1. Log into [Fathom](https://fathom.video)
2. Go to **Settings** → **API Access**
3. Click **Generate API Key** and save it
4. Click **Add** → **Setup Webhook**
5. Configure:
   - **Destination URL**: `https://your-render-app.onrender.com/webhook/fathom`
   - **Trigger for**: Your recordings
   - **Include**: ✅ Summary, ✅ Transcript, ✅ Action Items
6. Save and copy the **Webhook Secret** (format: `whsec_xxx`)

---

## Step 3: HubSpot Setup

### Create Private App

1. Log into HubSpot
2. Go to **Settings** → **Integrations** → **Private Apps**
3. Click **Create a private app**
4. Name it "Fathom CRM Agent"
5. Go to **Scopes** tab and add:
   - `crm.objects.companies.read`
   - `crm.objects.companies.write`
   - `crm.objects.contacts.read`
   - `crm.objects.notes.read`
   - `crm.objects.notes.write`
6. Click **Create app**
7. Copy the **Access Token** (format: `pat-xx-xxx...`)

---

## Step 4: Groq Setup

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / Log in
3. Go to **API Keys**
4. Create a new key and copy it (format: `gsk_xxx...`)

---

## Step 5: Resend Setup

### Create Account & Verify Domain

1. Go to [resend.com](https://resend.com) and create account
2. Go to **Domains** and add your domain (or use their test domain for development)
3. Follow DNS verification instructions
4. Go to **API Keys** and create a key (format: `re_xxx...`)

---

## Step 6: Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/fathom-crm-agent.git
cd fathom-crm-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env .env
# Edit .env with your API keys

# Initialize database
python -m app.core.database --init

# Run server
uvicorn app.main:app --reload --port 8000
```

### Test Locally with ngrok

To receive Fathom webhooks locally:

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000

# Use the ngrok URL as your Fathom webhook destination
# Example: https://abc123.ngrok.io/webhook/fathom
```

---

## Step 7: Deploy to Render

### Option A: One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Option B: Manual Deploy

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New** → **Web Service**
3. Connect your repository
4. Configure:
   - **Name**: fathom-crm-agent
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (copy from `.env.example`)
6. Deploy

### Update Fathom Webhook URL

After deployment, update your Fathom webhook to:
```
https://fathom-crm-agent.onrender.com/webhook/fathom
```

---

## Step 8: Verify Setup

1. **Health Check**: Visit `https://your-app.onrender.com/health`
2. **Test Webhook**: Record a short Fathom meeting
3. **Verify**:
   - Check Render logs for processing
   - Check HubSpot for new note
   - Check email for follow-up

---

## Troubleshooting

### Webhook Not Firing

- Verify webhook URL is correct in Fathom settings
- Check Render logs for incoming requests
- Ensure webhook secret matches

### HubSpot Company Not Found

- The company must exist in HubSpot with matching domain or name
- Check company domain spelling in HubSpot
- Review AI extraction in Render logs

### Email Not Received

- Verify Resend domain is verified
- Check spam folder
- Confirm `USER_EMAIL` is correct in environment

### Cold Start Delays

On Render free tier, the first request after 15 minutes of inactivity may take 10-30 seconds. Upgrade to Starter ($7/mo) for always-on.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `FATHOM_WEBHOOK_SECRET` | ✅ | Fathom webhook signing secret |
| `HUBSPOT_ACCESS_TOKEN` | ✅ | HubSpot private app token |
| `GROQ_API_KEY` | ✅ | Groq API key |
| `RESEND_API_KEY` | ✅ | Resend API key |
| `USER_EMAIL` | ✅ | Email for notifications |
| `EMAIL_FROM` | ❌ | Sender email address |
| `APP_ENV` | ❌ | `development` or `production` |
| `DEBUG` | ❌ | Enable debug logging |
