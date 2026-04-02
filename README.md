# Agent Transponder

**Automated meeting-to-CRM pipeline with AI-powered follow-up notes.**

Agent Transponder automatically processes your video call recordings, extracts actionable CRM notes using AI, uploads them to HubSpot, and emails you a professional follow-up summary — all without lifting a finger.

---

## What It Does

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌─────────────┐
│   Fathom     │────▶│  Fathom CRM      │────▶│  HubSpot    │────▶│   Email     │
│  (Meeting)   │     │  Agent (AI)      │     │  (CRM Note) │     │  (Summary)  │
└──────────────┘     └──────────────────┘     └─────────────┘     └─────────────┘
     Webhook              Claude/Groq LLM              REST API           Resend API
```

1. **You finish a meeting** recorded by Fathom
2. **Fathom sends a webhook** with transcript, summary, and action items
3. **AI extracts** company name, attendees, CRM-ready notes, and next steps
4. **HubSpot receives** a formatted note attached to the correct company
5. **You receive an email** with the follow-up summary and a link to the CRM record

---

## Features

- **Zero manual data entry** — meetings automatically sync to your CRM
- **AI-powered extraction** — Claude (claude-sonnet-4-20250514) identifies key information
- **Smart company matching** — finds the right HubSpot company by domain or name
- **Professional email summaries** — formatted follow-up notes delivered to your inbox
- **Audit trail** — all processed meetings logged in PostgreSQL

---

## Tech Stack

| Component | Technology                            | Purpose |
|-----------|---------------------------------------|---------|
| Backend | FastAPI (Python 3.11+)                | Webhook handling, API routing |
| Database | PostgreSQL (Neon)                     | User accounts, credentials, meeting logs |
| AI | Claude API / Groq API (Llama 3.1 70B) | Transcript processing, note extraction |
| CRM | HubSpot API                           | Company search, note creation |
| Email | Resend                                | Follow-up email delivery |
| Hosting | Railway / Render                      | Web service deployment |

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database (Neon free tier works)
- API keys for: Fathom, HubSpot, Claude / Groq, Resend

### 1. Clone and Install

```bash
git clone https://github.com/Shiv716/Agent-Transponder.git
cd agent-transponder
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env .env
# Edit .env with your API keys
```

### 3. Initialize Database

```bash
python -m app.core.database --init
```

### 4. Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Register Fathom Webhook

Point your Fathom webhook to:
```
https://your-domain.com/webhook/fathom
```

---

## Environment Variables

| Variable                | Description                          | Required |
|-------------------------|--------------------------------------|----------|
| `DATABASE_URL`          | PostgreSQL connection string         | ✅ |
| `LLM_API_KEY`           | LLM API key for LLM processing       | ✅ |
| `HUBSPOT_ACCESS_TOKEN`  | HubSpot private app access token     | ✅ |
| `RESEND_API_KEY`        | Resend API key for emails            | ✅ |
| `FATHOM_WEBHOOK_SECRET` | Fathom webhook signing secret        | ✅ |
| `USER_EMAIL`            | Email address for follow-up delivery | ✅ |
| `APP_ENV`               | `development` or `production`        | ❌ |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhook/fathom` | Receives Fathom meeting webhooks |
| `GET` | `/health` | Health check for monitoring |
| `GET` | `/meetings` | List processed meetings |
| `GET` | `/meetings/{id}` | Get specific meeting details |

---

## Project Structure

```
agent-transponder/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── core/
│   │   ├── config.py        # Environment configuration
│   │   └── database.py      # Database connection & models
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── routers/
│   │   ├── webhook.py       # Fathom webhook handler
│   │   └── meetings.py      # Meeting history endpoints
│   └── services/
│       ├── ai_processor.py  # LLM integration
│       ├── hubspot.py       # HubSpot API client
│       └── email.py         # Resend email service
├── tests/
│   └── test_webhook.py      # Webhook handler tests
├── docs/
│   ├── SETUP.md             # Detailed setup guide
│   └── ARCHITECTURE.md      # System design documentation
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── render.yaml              # Render deployment config
├── CONTRIBUTING.md 
└── README.md
```

---

## Deployment (Render)

### One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Manual Deploy

1. Create a new **Web Service** on Render
2. Connect your GitHub repository
3. Set environment variables in Render dashboard
4. Deploy

The included `render.yaml` handles build and start commands automatically.

---

## How AI Processing Works

The  LLM receives the meeting transcript and extracts:

```json
{
  "company_name": "Acme Corp",
  "company_domain": "acme.com",
  "attendees": ["John Smith", "Jane Doe"],
  "crm_note": "Discussed Q3 implementation timeline. Client confirmed budget approval. Next steps: send SOW by Friday.",
  "action_items": [
    "Send SOW document",
    "Schedule technical deep-dive",
    "Confirm stakeholder list"
  ],
  "meeting_sentiment": "positive",
  "deal_stage_signal": "negotiation"
}
```

This structured data drives the HubSpot update and email content.

---

## License

[MIT](LICENSE)

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/agent-transponder/issues)
- **Documentation**: [docs/](docs/)

---

Built with ☕ and AI.
