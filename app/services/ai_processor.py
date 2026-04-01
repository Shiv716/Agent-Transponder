"""
AI processing service using Groq (Llama 3.1 70B).

Extracts structured CRM data from meeting transcripts.
"""

import json
import logging
from typing import Optional
import httpx

from app.core.config import settings
from app.models.schemas import ExtractedMeetingData

logger = logging.getLogger(__name__)

# Groq API endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# OpenAI API endpoint
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# System prompt for CRM extraction
EXTRACTION_PROMPT = """You are an AI assistant that extracts CRM-relevant information from meeting transcripts.

Analyze the transcript and extract:
1. **Company Name**: The primary external company discussed (not your company)
2. **Company Domain**: Their website domain if mentioned or inferable
3. **Attendees**: List of people in the meeting
4. **CRM Note**: A concise, professional summary suitable for a CRM record (2-4 sentences)
5. **Action Items**: Specific next steps with owners if mentioned
6. **Meeting Sentiment**: positive, neutral, or negative
7. **Deal Stage Signal**: If sales-related, infer the stage (discovery, demo, negotiation, closed, etc.)
8. **Key Topics**: Main subjects discussed

Respond ONLY with valid JSON in this exact format:
{
    "company_name": "string or null",
    "company_domain": "string or null",
    "attendees": ["name1", "name2"],
    "crm_note": "Professional CRM summary here",
    "action_items": ["action 1", "action 2"],
    "meeting_sentiment": "positive|neutral|negative",
    "deal_stage_signal": "string or null",
    "key_topics": ["topic1", "topic2"]
}

If information is not available, use null for strings or empty arrays for lists.
Do NOT include any text outside the JSON object."""


async def extract_meeting_data(
    transcript: str,
    summary: Optional[str] = None,
    action_items: Optional[list] = None,
    meeting_title: Optional[str] = None,
) -> ExtractedMeetingData:
    """
    Extract structured CRM data from meeting content using Groq.
    
    Args:
        transcript: Full meeting transcript
        summary: Optional pre-generated summary from Fathom
        action_items: Optional action items from Fathom
        meeting_title: Optional meeting title for context
    
    Returns:
        ExtractedMeetingData with parsed fields
    """
    
    # Build context for the LLM
    context_parts = []
    
    if meeting_title:
        context_parts.append(f"Meeting Title: {meeting_title}")
    
    if summary:
        context_parts.append(f"Meeting Summary:\n{summary}")
    
    if action_items:
        items_text = "\n".join(f"- {item}" for item in action_items)
        context_parts.append(f"Action Items:\n{items_text}")
    
    # Truncate transcript if too long (Groq has ~8k context for this model)
    max_transcript_chars = 12000
    if len(transcript) > max_transcript_chars:
        transcript = transcript[:max_transcript_chars] + "\n\n[Transcript truncated...]"
    
    context_parts.append(f"Full Transcript:\n{transcript}")
    
    user_content = "\n\n---\n\n".join(context_parts)
    
    # Call Groq API
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": settings.openai_api_key,
        "messages": [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,  # Low temp for consistent extraction
        "max_tokens": 1000,
        "response_format": {"type": "json_object"},
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENAI_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            extracted = json.loads(content)
            
            logger.info(f"Successfully extracted meeting data: {extracted.get('company_name', 'Unknown')}")
            
            return ExtractedMeetingData(**extracted)
            
    except httpx.HTTPStatusError as e:
        logger.error(f"OPENAI API error: {e.response.status_code} - {e.response.text}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OPENAI response as JSON: {e}")
        # Return minimal data on parse failure
        return ExtractedMeetingData(
            crm_note="Meeting processed but AI extraction failed. Please review manually.",
            action_items=[],
        )
    except Exception as e:
        logger.error(f"Unexpected error in AI processing: {e}")
        raise


async def generate_email_content(
    meeting_title: str,
    crm_note: str,
    action_items: list,
    company_name: Optional[str],
    hubspot_url: Optional[str],
    fathom_url: str,
) -> tuple[str, str]:
    """
    Generate email subject and body for follow-up notification.
    
    Returns:
        Tuple of (subject, html_body)
    """
    
    subject = f"Meeting Follow-Up: {meeting_title or 'Your Recent Call'}"
    
    # Build action items HTML
    action_items_html = ""
    if action_items:
        items_list = "".join(f"<li>{item}</li>" for item in action_items)
        action_items_html = f"""
        <h3 style="color: #1a1a1a; margin-top: 24px;">Action Items</h3>
        <ul style="color: #4a4a4a; line-height: 1.6;">
            {items_list}
        </ul>
        """
    
    # Build CRM link section
    crm_link_html = ""
    if hubspot_url:
        crm_link_html = f"""
        <p style="margin-top: 16px;">
            <a href="{hubspot_url}" 
               style="background-color: #ff7a59; color: white; padding: 10px 20px; 
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                View in HubSpot
            </a>
        </p>
        """
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                 max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
        <div style="background-color: white; padding: 32px; border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            
            <h2 style="color: #1a1a1a; margin-top: 0;">
                {meeting_title or 'Meeting Summary'}
            </h2>
            
            {f'<p style="color: #666; font-size: 14px;">Company: {company_name}</p>' if company_name else ''}
            
            <h3 style="color: #1a1a1a; margin-top: 24px;">Summary</h3>
            <p style="color: #4a4a4a; line-height: 1.6;">
                {crm_note}
            </p>
            
            {action_items_html}
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
            
            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                {crm_link_html}
                <p>
                    <a href="{fathom_url}" 
                       style="background-color: #6366f1; color: white; padding: 10px 20px; 
                              text-decoration: none; border-radius: 4px; display: inline-block;">
                        Watch Recording
                    </a>
                </p>
            </div>
            
            <p style="color: #999; font-size: 12px; margin-top: 24px;">
                Automatically generated by Agent Transponder
            </p>
        </div>
    </body>
    </html>
    """
    
    return subject, html_body
