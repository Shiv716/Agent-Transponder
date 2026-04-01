"""
Demo data and test endpoints for development.

Allows testing the full pipeline without a real Fathom webhook.
"""

from datetime import datetime, timedelta, timezone

# Demo payload matching Fathom webhook schema
DEMO_FATHOM_PAYLOAD = {
    "recording_id": 987654321,
    "type": "meeting_content_ready",
    "title": "Q2 Partnership Discussion - Acme Corp",
    "meeting_title": "Q2 Partnership Discussion - Acme Corp",
    "url": "https://fathom.video/calls/987654321",
    "share_url": "https://fathom.video/share/demo123abc",
    "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z",
    "scheduled_start_time": (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z",
    "scheduled_end_time": (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z",
    "recording_start_time": (datetime.utcnow() - timedelta(minutes=58)).isoformat() + "Z",
    "recording_end_time": (datetime.utcnow() - timedelta(minutes=32)).isoformat() + "Z",
    "calendar_invitees_domains_type": "external",
    "transcript": [
        {
            "speaker": "John Smith",
            "timestamp": "00:00:15",
            "text": "Thanks for joining today. I'm John from Acme Corp, and we're really excited to discuss the Q2 partnership."
        },
        {
            "speaker": "Sarah Johnson",
            "timestamp": "00:00:32",
            "text": "Thanks John. Happy to be here. I've reviewed your proposal and I think there's a lot of potential."
        },
        {
            "speaker": "John Smith",
            "timestamp": "00:01:05",
            "text": "Great to hear. So our main goal is to integrate your platform with our existing CRM workflow. We're looking at about 500 users initially."
        },
        {
            "speaker": "Sarah Johnson",
            "timestamp": "00:01:28",
            "text": "That's a solid starting point. For that user count, I'd recommend our Professional tier. It includes API access and dedicated support."
        },
        {
            "speaker": "John Smith",
            "timestamp": "00:02:10",
            "text": "What's the timeline for implementation? We're hoping to go live by end of April."
        },
        {
            "speaker": "Sarah Johnson",
            "timestamp": "00:02:25",
            "text": "Typically 4-6 weeks for full integration. If we kick off next week, April is definitely achievable."
        },
        {
            "speaker": "John Smith",
            "timestamp": "00:03:00",
            "text": "Perfect. Budget is already approved on our end. Can you send over the SOW by Friday?"
        },
        {
            "speaker": "Sarah Johnson",
            "timestamp": "00:03:15",
            "text": "Absolutely. I'll have it in your inbox by Thursday. Should we schedule a technical deep-dive with your engineering team next week?"
        },
        {
            "speaker": "John Smith",
            "timestamp": "00:03:35",
            "text": "Yes, that would be ideal. I'll loop in our CTO, Mike Chen. How about Tuesday at 2pm?"
        },
        {
            "speaker": "Sarah Johnson",
            "timestamp": "00:03:50",
            "text": "Tuesday works. I'll send a calendar invite. Looking forward to getting this partnership started."
        }
    ],
    "default_summary": {
        "template_name": "general",
        "markdown_formatted": """## Meeting Summary

**Participants:** John Smith (Acme Corp), Sarah Johnson

**Purpose:** Discuss Q2 partnership and platform integration

## Key Discussion Points

- Acme Corp wants to integrate the platform with their existing CRM workflow
- Initial rollout planned for 500 users
- Professional tier recommended for API access and dedicated support
- Implementation timeline: 4-6 weeks
- Target go-live: End of April
- Budget already approved by Acme Corp

## Decisions Made

- Proceeding with Professional tier
- Technical deep-dive scheduled for Tuesday at 2pm with CTO Mike Chen

## Next Steps

1. Sarah to send SOW by Thursday
2. Technical deep-dive meeting Tuesday 2pm
3. Kick off implementation next week
"""
    },
    "action_items": [
        {
            "text": "Send SOW by Thursday",
            "assignee": "Sarah Johnson"
        },
        {
            "text": "Schedule technical deep-dive for Tuesday 2pm",
            "assignee": "Sarah Johnson"
        },
        {
            "text": "Loop in CTO Mike Chen for technical meeting",
            "assignee": "John Smith"
        },
        {
            "text": "Kick off implementation next week",
            "assignee": "Both"
        }
    ],
    "calendar_invitees": [
        {
            "name": "John Smith",
            "email": "john.smith@acmecorp.com",
            "is_external": True
        },
        {
            "name": "Sarah Johnson",
            "email": "sarah@yourcompany.com",
            "is_external": False
        }
    ],
    "recorded_by": {
        "name": "Sarah Johnson",
        "email": "sarah@yourcompany.com"
    },
    "crm_matches": {
        "company": {
            "id": "12345",
            "name": "Acme Corp",
            "domain": "acmecorp.com"
        }
    }
}


def get_demo_payload() -> dict:
    """Get demo payload with fresh timestamps."""
    payload = DEMO_FATHOM_PAYLOAD.copy()

    now = datetime.now(timezone.utc)
    payload["created_at"] = (now - timedelta(hours=1)).isoformat() + "Z"
    payload["scheduled_start_time"] = (now - timedelta(hours=1)).isoformat() + "Z"
    payload["scheduled_end_time"] = (now - timedelta(minutes=30)).isoformat() + "Z"
    payload["recording_start_time"] = (now - timedelta(minutes=58)).isoformat() + "Z"
    payload["recording_end_time"] = (now - timedelta(minutes=32)).isoformat() + "Z"
    payload["recording_id"] = int(now.timestamp())

    return payload


def get_transcript_text(transcript: list) -> str:
    """Convert transcript array to plain text."""
    lines = []
    for entry in transcript:
        speaker = entry.get("speaker", "Unknown")
        text = entry.get("text", "")
        lines.append(f"{speaker}: {text}")
    return "\n\n".join(lines)