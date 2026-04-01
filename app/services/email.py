"""
Email service using Resend.

Sends follow-up notification emails to users.
"""

import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Resend API endpoint
RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
) -> Optional[str]:
    """
    Send an email via Resend.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html_body: HTML email content
        from_email: Optional sender (uses default from settings)
    
    Returns:
        Email ID if sent successfully, None otherwise
    """
    
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "from": from_email or settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html_body,
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(RESEND_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            email_id = data.get("id")
            
            logger.info(f"Email sent successfully: {email_id} to {to}")
            return email_id
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Resend API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return None


async def send_meeting_followup(
    to: str,
    meeting_title: str,
    crm_note: str,
    action_items: list,
    company_name: Optional[str],
    hubspot_url: Optional[str],
    fathom_url: str,
) -> Optional[str]:
    """
    Send a formatted meeting follow-up email.
    
    Args:
        to: Recipient email
        meeting_title: Meeting title
        crm_note: CRM summary note
        action_items: List of action items
        company_name: Company name (if identified)
        hubspot_url: Link to HubSpot company record
        fathom_url: Link to Fathom recording
    
    Returns:
        Email ID if sent successfully
    """
    
    from app.services.ai_processor import generate_email_content
    
    subject, html_body = await generate_email_content(
        meeting_title=meeting_title,
        crm_note=crm_note,
        action_items=action_items,
        company_name=company_name,
        hubspot_url=hubspot_url,
        fathom_url=fathom_url,
    )
    
    return await send_email(to=to, subject=subject, html_body=html_body)
