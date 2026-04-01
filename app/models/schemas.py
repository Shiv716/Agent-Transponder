"""
Pydantic models for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


# ============================================================================
# Fathom Webhook Schemas
# ============================================================================

class FathomWebhookPayload(BaseModel):
    """Incoming Fathom webhook payload."""
    
    recording_id: int = Field(..., description="Fathom recording ID")
    url: str = Field(..., description="Fathom recording URL")
    share_url: Optional[str] = Field(None, description="Shareable URL")
    type: str = Field(..., description="Event type (meeting_content_ready)")
    
    # Meeting metadata
    title: Optional[str] = Field(None, description="Meeting title")
    created_at: Optional[str] = Field(None)
    scheduled_start_time: Optional[str] = Field(None)
    scheduled_end_time: Optional[str] = Field(None)
    recording_start_time: Optional[str] = Field(None)
    recording_end_time: Optional[str] = Field(None)
    
    # Content (when include_* flags are set on webhook)
    transcript: Optional[str] = Field(None, description="Full transcript text")
    summary: Optional[dict] = Field(None, description="AI summary object")
    action_items: Optional[List[dict]] = Field(None, description="Action items list")
    
    class Config:
        extra = "allow"  # Allow additional fields from Fathom


class FathomSummary(BaseModel):
    """Fathom summary structure."""
    
    template_name: Optional[str] = None
    markdown_formatted: Optional[str] = None
    plain_text: Optional[str] = None


# ============================================================================
# AI Extraction Schemas
# ============================================================================

class ExtractedMeetingData(BaseModel):
    """Data extracted from meeting transcript by LLM."""
    
    company_name: Optional[str] = Field(None, description="Primary company discussed")
    company_domain: Optional[str] = Field(None, description="Company website domain")
    attendees: List[str] = Field(default_factory=list, description="Meeting attendees")
    crm_note: str = Field(..., description="Formatted CRM note for HubSpot")
    action_items: List[str] = Field(default_factory=list, description="Action items")
    meeting_sentiment: Optional[str] = Field(None, description="positive/neutral/negative")
    deal_stage_signal: Optional[str] = Field(None, description="Inferred deal stage")
    key_topics: List[str] = Field(default_factory=list, description="Main discussion topics")


# ============================================================================
# HubSpot Schemas
# ============================================================================

class HubSpotCompany(BaseModel):
    """HubSpot company record."""
    
    id: str
    name: str
    domain: Optional[str] = None
    properties: Optional[dict] = None


class HubSpotNoteCreate(BaseModel):
    """Payload for creating a HubSpot note."""
    
    company_id: str
    note_body: str
    timestamp: Optional[datetime] = None


class HubSpotNoteResponse(BaseModel):
    """Response from HubSpot note creation."""
    
    id: str
    created_at: datetime


# ============================================================================
# API Response Schemas
# ============================================================================

class MeetingResponse(BaseModel):
    """Meeting record response."""
    
    id: UUID
    fathom_recording_id: str
    fathom_url: str
    meeting_title: Optional[str]
    company_name: Optional[str]
    company_domain: Optional[str]
    crm_note: Optional[str]
    hubspot_company_id: Optional[str]
    hubspot_note_id: Optional[str]
    email_sent_at: Optional[datetime]
    meeting_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """List of meetings response."""
    
    meetings: List[MeetingResponse]
    total: int


class WebhookResponse(BaseModel):
    """Response to webhook processing."""
    
    status: str
    message: str
    meeting_id: Optional[str] = None
    hubspot_note_id: Optional[str] = None
    email_sent: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
