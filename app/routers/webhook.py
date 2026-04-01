"""
Webhook endpoints for receiving external service callbacks.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db, Meeting
from app.models.schemas import FathomWebhookPayload, WebhookResponse
from app.services.ai_processor import extract_meeting_data
from app.services.hubspot import get_hubspot_client
from app.services.email import send_meeting_followup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])


def verify_fathom_signature(
    payload_body: bytes,
    signature_header: str,
    webhook_secret: str,
) -> bool:
    """
    Verify Fathom webhook signature.
    
    Fathom uses HMAC-SHA256 for webhook verification.
    The signature header format: v1,<signature>
    """
    
    if not signature_header:
        return False
    
    try:
        # Extract signatures (may be multiple, space-delimited)
        signatures = []
        for part in signature_header.split(" "):
            if "," in part:
                version, sig = part.split(",", 1)
                if version == "v1":
                    signatures.append(sig)
        
        if not signatures:
            return False
        
        # Compute expected signature
        # Fathom secret format: whsec_<base64_secret>
        secret = webhook_secret
        if secret.startswith("whsec_"):
            import base64
            secret = base64.b64decode(secret[6:])
        else:
            secret = secret.encode()
        
        expected = hmac.new(
            secret,
            payload_body,
            hashlib.sha256,
        ).hexdigest()
        
        # Compare (constant time)
        return any(hmac.compare_digest(expected, sig) for sig in signatures)
        
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


async def process_fathom_webhook(
    payload: FathomWebhookPayload,
    db: AsyncSession,
):
    """
    Background task to process Fathom webhook.
    
    1. Extract data with AI
    2. Find/create HubSpot company
    3. Create HubSpot note
    4. Send follow-up email
    5. Log to database
    """
    
    logger.info(f"Processing Fathom webhook for recording: {payload.recording_id}")
    
    try:
        # Get transcript content
        transcript = payload.transcript or ""
        
        # Get summary content
        summary_text = None
        if payload.summary:
            summary_text = (
                payload.summary.get("markdown_formatted") 
                or payload.summary.get("plain_text")
                or str(payload.summary)
            )
        
        # Get action items
        action_items_list = []
        if payload.action_items:
            action_items_list = [
                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                for item in payload.action_items
            ]
        
        # If no transcript, use summary as fallback
        if not transcript and summary_text:
            transcript = summary_text
        
        if not transcript:
            logger.warning(f"No transcript or summary for recording {payload.recording_id}")
            transcript = f"Meeting: {payload.title or 'Untitled'}"
        
        # 1. Extract meeting data with AI
        extracted = await extract_meeting_data(
            transcript=transcript,
            summary=summary_text,
            action_items=action_items_list,
            meeting_title=payload.title,
        )
        
        logger.info(f"Extracted data - Company: {extracted.company_name}, Domain: {extracted.company_domain}")
        
        # 2. Find HubSpot company
        hubspot = get_hubspot_client()
        company = await hubspot.find_company(
            company_name=extracted.company_name,
            company_domain=extracted.company_domain,
        )
        
        hubspot_company_id = None
        hubspot_note_id = None
        hubspot_url = None
        
        if company:
            hubspot_company_id = company.id
            hubspot_url = hubspot.get_company_url(company.id)
            
            # 3. Create HubSpot note
            # Format note with metadata
            note_body = f"""<strong>Meeting:</strong> {payload.title or 'Untitled Meeting'}<br><br>
<strong>Summary:</strong><br>
{extracted.crm_note}<br><br>
<strong>Action Items:</strong><br>
{'<br>'.join(f'• {item}' for item in extracted.action_items) if extracted.action_items else 'None identified'}<br><br>
<a href="{payload.url}">View Fathom Recording</a>
"""
            
            hubspot_note_id = await hubspot.create_note(
                company_id=company.id,
                note_body=note_body,
            )
            
            logger.info(f"Created HubSpot note: {hubspot_note_id}")
        else:
            logger.warning(f"No HubSpot company found for: {extracted.company_name}")
        
        # 4. Send follow-up email
        email_sent_at = None
        email_id = await send_meeting_followup(
            to=settings.user_email,
            meeting_title=payload.title or "Your Recent Meeting",
            crm_note=extracted.crm_note,
            action_items=extracted.action_items,
            company_name=extracted.company_name,
            hubspot_url=hubspot_url,
            fathom_url=payload.url,
        )
        
        if email_id:
            email_sent_at = datetime.utcnow()
            logger.info(f"Sent follow-up email: {email_id}")
        
        # 5. Log to database
        meeting = Meeting(
            fathom_recording_id=str(payload.recording_id),
            fathom_url=payload.url,
            fathom_share_url=payload.share_url,
            meeting_title=payload.title,
            company_name=extracted.company_name,
            company_domain=extracted.company_domain,
            attendees=json.dumps(extracted.attendees),
            crm_note=extracted.crm_note,
            action_items=json.dumps(extracted.action_items),
            full_summary=summary_text,
            hubspot_company_id=hubspot_company_id,
            hubspot_note_id=hubspot_note_id,
            email_sent_at=email_sent_at,
            email_recipient=settings.user_email,
            meeting_date=datetime.fromisoformat(payload.scheduled_start_time.replace("Z", "+00:00")) if payload.scheduled_start_time else datetime.utcnow(),
        )
        
        db.add(meeting)
        await db.commit()
        
        logger.info(f"Successfully processed meeting {payload.recording_id}")
        
    except Exception as e:
        logger.exception(f"Error processing Fathom webhook: {e}")
        raise


@router.post("/fathom", response_model=WebhookResponse)
async def fathom_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive and process Fathom meeting webhooks.
    
    This endpoint is called by Fathom after a meeting recording is processed.
    Processing happens in the background to return quickly to Fathom.
    """
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature (optional in development)
    signature = request.headers.get("webhook-signature", "")
    
    if settings.app_env == "production":
        if not verify_fathom_signature(body, signature, settings.fathom_webhook_secret):
            logger.warning("Invalid Fathom webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    try:
        payload_dict = json.loads(body)
        payload = FathomWebhookPayload(**payload_dict)
    except Exception as e:
        logger.error(f"Failed to parse Fathom webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    
    # Check for duplicate
    existing = await db.execute(
        select(Meeting).where(Meeting.fathom_recording_id == str(payload.recording_id))
    )
    if existing.scalar_one_or_none():
        logger.info(f"Duplicate webhook for recording {payload.recording_id}, skipping")
        return WebhookResponse(
            status="skipped",
            message="Recording already processed",
        )
    
    # Process in background
    background_tasks.add_task(process_fathom_webhook, payload, db)
    
    return WebhookResponse(
        status="accepted",
        message="Webhook received, processing in background",
    )
