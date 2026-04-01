# Architecture

Technical architecture and design decisions for Agent Transponder.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SERVICES                               │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────┤
│     Fathom      │     HubSpot     │      Groq       │        Resend         │
│  (Recordings)   │     (CRM)       │     (LLM)       │       (Email)         │
└────────┬────────┴────────┬────────┴────────┬────────┴───────────┬───────────┘
         │                 │                 │                    │
         │ Webhook         │ REST API        │ REST API           │ REST API
         │                 │                 │                    │
┌────────▼─────────────────▼─────────────────▼────────────────────▼───────────┐
│                                                                              │
│                         AGENT TRANSPONDER (FastAPI)                         │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Webhook    │  │     AI       │  │   HubSpot    │  │    Email     │    │
│  │   Router     │──│  Processor   │──│   Service    │──│   Service    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                                                                    │
│         │                                                                    │
│  ┌──────▼───────────────────────────────────────────────────────────────┐  │
│  │                        PostgreSQL (Neon)                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  meetings: id, fathom_id, company, crm_note, hubspot_id, ...   │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Webhook Reception

```
Fathom Meeting Ends
        │
        ▼
┌───────────────────┐
│ POST /webhook/    │
│      fathom       │
├───────────────────┤
│ • Verify signature│
│ • Parse payload   │
│ • Check duplicate │
│ • Queue background│
└─────────┬─────────┘
          │
          ▼
    Return 202
    (Accepted)
```

### 2. Background Processing

```
Background Task
        │
        ▼
┌───────────────────┐
│   AI Extraction   │
│      (Groq)       │
├───────────────────┤
│ • Company name    │
│ • Domain          │
│ • Attendees       │
│ • CRM note        │
│ • Action items    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  HubSpot Search   │
├───────────────────┤
│ • Search by domain│
│ • Fallback: name  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Create HubSpot   │
│      Note         │
├───────────────────┤
│ • Format HTML     │
│ • Associate to    │
│   company         │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Send Email      │
│    (Resend)       │
├───────────────────┤
│ • HTML template   │
│ • CRM link        │
│ • Fathom link     │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Log to Database  │
└───────────────────┘
```

---

## Component Details

### Webhook Router (`app/routers/webhook.py`)

**Responsibilities:**
- Receive Fathom POST requests
- Verify HMAC-SHA256 signature
- Parse and validate payload
- Prevent duplicate processing
- Dispatch to background task

**Security:**
- Signature verification in production
- Constant-time comparison to prevent timing attacks
- Payload validation with Pydantic

### AI Processor (`app/services/ai_processor.py`)

**Responsibilities:**
- Build context from transcript + summary + action items
- Call Groq API with structured extraction prompt
- Parse JSON response into typed model
- Generate email HTML content

**Model:** Llama 3.1 70B (via Groq)

**Prompt Strategy:**
- System prompt defines exact JSON schema
- Low temperature (0.1) for consistent extraction
- Response format enforced as JSON object

**Extracted Fields:**
```python
{
    "company_name": str | None,
    "company_domain": str | None,
    "attendees": list[str],
    "crm_note": str,
    "action_items": list[str],
    "meeting_sentiment": "positive" | "neutral" | "negative",
    "deal_stage_signal": str | None,
    "key_topics": list[str]
}
```

### HubSpot Service (`app/services/hubspot.py`)

**Responsibilities:**
- Search companies by domain (preferred) or name
- Create notes with company association
- Generate HubSpot record URLs

**API Endpoints Used:**
- `POST /crm/v3/objects/companies/search`
- `POST /crm/v3/objects/notes`

**Association Type:**
- Note to Company: `associationTypeId: 190`

### Email Service (`app/services/email.py`)

**Responsibilities:**
- Send HTML emails via Resend API
- Format meeting follow-up templates

**Template Includes:**
- Meeting title and company
- CRM summary note
- Action items list
- HubSpot link button
- Fathom recording link button

---

## Database Schema

### `meetings` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `fathom_recording_id` | VARCHAR(100) | Fathom's recording ID (unique) |
| `fathom_url` | TEXT | Link to Fathom recording |
| `fathom_share_url` | TEXT | Shareable Fathom link |
| `meeting_title` | VARCHAR(500) | Meeting title from calendar |
| `company_name` | VARCHAR(255) | Extracted company name |
| `company_domain` | VARCHAR(255) | Extracted company domain |
| `attendees` | TEXT | JSON array of attendee names |
| `crm_note` | TEXT | AI-generated CRM note |
| `action_items` | TEXT | JSON array of action items |
| `full_summary` | TEXT | Original Fathom summary |
| `hubspot_company_id` | VARCHAR(50) | HubSpot company record ID |
| `hubspot_note_id` | VARCHAR(50) | Created HubSpot note ID |
| `email_sent_at` | TIMESTAMP | When follow-up email was sent |
| `email_recipient` | VARCHAR(255) | Email recipient address |
| `meeting_date` | TIMESTAMP | Original meeting date |
| `created_at` | TIMESTAMP | Record creation time |
| `processed_at` | TIMESTAMP | Processing completion time |

**Indexes:**
- Primary: `id`
- Unique: `fathom_recording_id`

---

## Error Handling

### Webhook Errors

| Error | HTTP Code | Handling |
|-------|-----------|----------|
| Invalid signature | 401 | Reject request |
| Invalid payload | 400 | Reject request |
| Duplicate recording | 200 | Return "skipped" status |
| Processing failure | N/A | Log error, don't retry |

### Service Errors

| Service | Error | Handling |
|---------|-------|----------|
| Groq | API error | Return minimal extraction |
| Groq | JSON parse fail | Return fallback note |
| HubSpot | Company not found | Skip note creation |
| HubSpot | Note creation fail | Log and continue |
| Resend | Send failure | Log and continue |

**Design Principle:** Fail gracefully. A failure in one service shouldn't block others.

---

## Security Considerations

### Secrets Management

- All secrets in environment variables
- Never logged or exposed in responses
- `.env` excluded from git

### Webhook Security

- HMAC-SHA256 signature verification
- Timestamp validation (replay attack prevention)
- Constant-time signature comparison

### API Security

- HTTPS only in production
- CORS configured appropriately
- No authentication on webhook (signature-based)
- Docs disabled in production

---

## Scalability Notes

### Current Design (Single User)

- One set of credentials in environment
- All meetings processed for one HubSpot account
- Single email recipient

### Future Multi-Tenant Design

To support multiple users:

1. Add `users` table with OAuth tokens
2. Store per-user Fathom webhook secrets
3. Store per-user HubSpot refresh tokens
4. Route webhooks by user identification
5. Add authentication to API endpoints

---

## Performance

### Webhook Response Time

- Target: < 500ms
- Processing happens in background
- Immediate 202 response to Fathom

### Background Processing

- Groq API: ~2-5 seconds
- HubSpot API: ~1-2 seconds
- Resend API: ~1 second
- Total: ~5-10 seconds per meeting

### Cold Start (Render Free Tier)

- First request after 15min idle: 10-30 seconds
- Mitigation: Upgrade to Starter plan ($7/mo)

---

## Monitoring

### Health Check

`GET /health` returns:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### Logging

- Structured logging with timestamps
- Log levels: DEBUG (dev), INFO (prod)
- Key events logged:
  - Webhook received
  - AI extraction results
  - HubSpot operations
  - Email sent
  - Errors with stack traces

### Recommended Additions

- Sentry for error tracking
- Render metrics for performance
- Uptime monitoring (e.g., UptimeRobot)
