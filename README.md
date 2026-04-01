# Agent Transponder

Automated meeting-to-CRM pipeline powered by AI.

---

## What it does

Agent Transponder listens for completed Fathom recordings, processes the transcript with Claude AI to extract structured insights, and automatically creates formatted meeting notes on the corresponding HubSpot company record. A follow-up email is sent to the user with the summary, action items, and direct links.

**Pipeline flow:**

```
Fathom webhook → Claude AI extraction → HubSpot note → Email digest
```

---

## The problem

Sales and customer success teams spend hours after meetings manually:
- Reviewing recordings and transcripts
- Writing up meeting summaries
- Logging notes in the CRM
- Tracking action items and follow-ups

This creates lag between the meeting and the CRM update, leading to stale data and missed follow-ups.

---

## How it adds value

| Before | After |
|--------|-------|
| Manual transcript review | Automatic AI extraction |
| Copy-paste into CRM | Direct HubSpot integration |
| Forgotten action items | Email digest with next steps |
| 15-30 min per meeting | Zero manual effort |

**Key benefits:**

- **Real-time sync** — Notes appear in HubSpot within seconds of meeting completion
- **Consistent formatting** — Every meeting note follows the same structure
- **No context switching** — Stay in your workflow, data flows automatically
- **Audit trail** — Every meeting linked to company record with timestamp

---

## Tech stack

| Component | Service |
|-----------|---------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL (Neon) |
| LLM | Claude claude-sonnet-4-20250514 |
| CRM | HubSpot |
| Email | Resend |
| Hosting | Railway |

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhook/fathom` | Receives Fathom webhook payload |
| `POST` | `/webhook/test` | Triggers test with demo data |
| `GET` | `/health` | Health check |
| `GET` | `/meetings` | List processed meetings |

---

## Environment variables

```
DATABASE_URL=postgresql://...
FATHOM_WEBHOOK_SECRET=whsec_...
HUBSPOT_ACCESS_TOKEN=pat-...
HUBSPOT_PORTAL_ID=...
ANTHROPIC_API_KEY=sk-ant-...
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@yourdomain.com
USER_EMAIL=you@example.com
```

---

## Quick start

1. Clone the repo
2. Set environment variables
3. Deploy to Railway (or run locally with `uvicorn app.main:app`)
4. Configure Fathom webhook URL: `https://your-app.up.railway.app/webhook/fathom`
5. Connect HubSpot with a private app token

---

## Dashboard

A standalone dashboard is available on the `deployPage` branch for GitHub Pages hosting. It provides:

- Integration status overview
- Test webhook trigger
- Activity log

The dashboard calls the Railway API directly via CORS-enabled endpoints.

---

## License

[MIT](LICENSE)
