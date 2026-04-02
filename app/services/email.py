"""
Email service using Resend.

Sends follow-up notification emails to users.
"""

import logging
from typing import Optional
import httpx
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

# Resend API endpoint
RESEND_API_URL = "https://api.resend.com/emails"

# Styled email template matching dashboard theme
EMAIL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #09090b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #09090b; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #141418; border-radius: 8px; border: 1px solid #27272a;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 32px 24px 32px; border-bottom: 1px solid #27272a;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <span style="color: #3b82f6; font-size: 14px; font-weight: 600;">Agent Transponder</span>
                                    </td>
                                    <td align="right">
                                        <span style="background-color: rgba(34, 197, 94, 0.15); color: #22c55e; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Processed</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Meeting Title -->
                    <tr>
                        <td style="padding: 32px 32px 16px 32px;">
                            <h1 style="margin: 0; color: #fafafa; font-size: 20px; font-weight: 600; line-height: 1.4;">{meeting_title}</h1>
                            <p style="margin: 8px 0 0 0; color: #a1a1aa; font-size: 14px;">{company_name} • {meeting_date}</p>
                        </td>
                    </tr>
                    
                    <!-- Summary Section -->
                    <tr>
                        <td style="padding: 0 32px 24px 32px;">
                            <div style="background-color: #0f0f12; border: 1px solid #27272a; border-radius: 6px; padding: 20px;">
                                <h2 style="margin: 0 0 12px 0; color: #a1a1aa; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Summary</h2>
                                <p style="margin: 0; color: #fafafa; font-size: 14px; line-height: 1.6;">{summary}</p>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Action Items -->
                    <tr>
                        <td style="padding: 0 32px 24px 32px;">
                            <div style="background-color: #0f0f12; border: 1px solid #27272a; border-radius: 6px; padding: 20px;">
                                <h2 style="margin: 0 0 12px 0; color: #a1a1aa; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Action Items</h2>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                    {action_items_html}
                                </table>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- CTA Buttons -->
                    <tr>
                        <td style="padding: 0 32px 32px 32px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td width="48%" align="center">
                                        <a href="{hubspot_url}" style="display: inline-block; width: 100%; padding: 14px 24px; background-color: #3b82f6; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 500; border-radius: 6px; text-align: center; box-sizing: border-box;">View in HubSpot</a>
                                    </td>
                                    <td width="4%"></td>
                                    <td width="48%" align="center">
                                        <a href="{recording_url}" style="display: inline-block; width: 100%; padding: 14px 24px; background-color: transparent; color: #fafafa; text-decoration: none; font-size: 14px; font-weight: 500; border-radius: 6px; border: 1px solid #27272a; text-align: center; box-sizing: border-box;">Watch Recording</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; border-top: 1px solid #27272a;">
                            <p style="margin: 0; color: #52525b; font-size: 12px; text-align: center;">
                                Automatically processed by Agent Transponder
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
'''


def _generate_action_items_html(action_items: list) -> str:
    """Generate HTML rows for action items."""
    if not action_items:
        return '<tr><td style="color: #a1a1aa; font-size: 14px;">No action items identified</td></tr>'
    
    rows = []
    for item in action_items:
        row = f'''
        <tr>
            <td style="padding: 8px 0; border-bottom: 1px solid #27272a;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td width="24" valign="top" style="padding-right: 12px;">
                            <div style="width: 18px; height: 18px; border: 2px solid #3b82f6; border-radius: 4px;"></div>
                        </td>
                        <td style="color: #fafafa; font-size: 14px; line-height: 1.5;">{item}</td>
                    </tr>
                </table>
            </td>
        </tr>
        '''
        rows.append(row)
    return ''.join(rows)


def _build_email_html(
    meeting_title: str,
    company_name: str,
    summary: str,
    action_items: list,
    hubspot_url: str,
    recording_url: str,
) -> str:
    """Build the complete styled email HTML."""
    action_items_html = _generate_action_items_html(action_items)
    meeting_date = datetime.now().strftime("%B %d, %Y")
    
    return EMAIL_TEMPLATE.format(
        meeting_title=meeting_title,
        company_name=company_name or "Unknown Company",
        meeting_date=meeting_date,
        summary=summary,
        action_items_html=action_items_html,
        hubspot_url=hubspot_url or "#",
        recording_url=recording_url or "#",
    )


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
    
    # Build styled email
    subject = f"Meeting Summary: {meeting_title}"
    html_body = _build_email_html(
        meeting_title=meeting_title,
        company_name=company_name,
        summary=crm_note,
        action_items=action_items,
        hubspot_url=hubspot_url,
        recording_url=fathom_url,
    )
    
    return await send_email(to=to, subject=subject, html_body=html_body)
