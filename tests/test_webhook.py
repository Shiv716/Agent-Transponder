"""
Tests for Fathom webhook handling.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import FathomWebhookPayload, ExtractedMeetingData


# Test client
client = TestClient(app)


# Sample Fathom webhook payload
SAMPLE_PAYLOAD = {
    "recording_id": 123456789,
    "url": "https://fathom.video/calls/123456789",
    "share_url": "https://fathom.video/share/abc123",
    "type": "meeting_content_ready",
    "title": "Sales Call - Acme Corp",
    "created_at": "2024-01-15T10:00:00Z",
    "scheduled_start_time": "2024-01-15T10:00:00Z",
    "scheduled_end_time": "2024-01-15T10:30:00Z",
    "recording_start_time": "2024-01-15T10:01:00Z",
    "recording_end_time": "2024-01-15T10:28:00Z",
    "transcript": """
        John: Hi everyone, thanks for joining. I'm John from Acme Corp.
        Sarah: Thanks John, excited to discuss the partnership.
        John: So we're looking at implementing your solution in Q2.
        Sarah: Great, let me walk you through our onboarding process.
        John: Perfect. Our budget is approved for this quarter.
        Sarah: Excellent. I'll send over the SOW by Friday.
        John: Sounds good. Let's schedule a technical deep-dive next week.
    """,
    "summary": {
        "template_name": "general",
        "markdown_formatted": "## Summary\nDiscussed Q2 implementation with Acme Corp. Budget approved."
    },
    "action_items": [
        {"text": "Send SOW by Friday"},
        {"text": "Schedule technical deep-dive"},
    ]
}


class TestHealthCheck:
    """Tests for health endpoint."""
    
    def test_health_check(self):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestWebhookPayloadParsing:
    """Tests for Fathom payload parsing."""
    
    def test_parse_valid_payload(self):
        """Valid payload parses correctly."""
        payload = FathomWebhookPayload(**SAMPLE_PAYLOAD)
        
        assert payload.recording_id == 123456789
        assert payload.url == "https://fathom.video/calls/123456789"
        assert payload.title == "Sales Call - Acme Corp"
        assert payload.transcript is not None
        assert len(payload.action_items) == 2
    
    def test_parse_minimal_payload(self):
        """Minimal payload with only required fields."""
        minimal = {
            "recording_id": 1,
            "url": "https://fathom.video/calls/1",
            "type": "meeting_content_ready",
        }
        payload = FathomWebhookPayload(**minimal)
        
        assert payload.recording_id == 1
        assert payload.transcript is None
        assert payload.action_items is None
    
    def test_parse_extra_fields(self):
        """Payload with extra fields doesn't fail."""
        with_extra = {
            **SAMPLE_PAYLOAD,
            "unknown_field": "some value",
            "another_field": 123,
        }
        payload = FathomWebhookPayload(**with_extra)
        assert payload.recording_id == 123456789


class TestExtractedMeetingData:
    """Tests for AI extraction model."""
    
    def test_valid_extraction(self):
        """Valid extraction data."""
        data = ExtractedMeetingData(
            company_name="Acme Corp",
            company_domain="acme.com",
            attendees=["John Smith", "Sarah Jones"],
            crm_note="Discussed Q2 implementation. Budget approved.",
            action_items=["Send SOW", "Schedule deep-dive"],
            meeting_sentiment="positive",
            deal_stage_signal="negotiation",
            key_topics=["implementation", "budget", "timeline"],
        )
        
        assert data.company_name == "Acme Corp"
        assert len(data.attendees) == 2
        assert len(data.action_items) == 2
    
    def test_minimal_extraction(self):
        """Extraction with only required fields."""
        data = ExtractedMeetingData(
            crm_note="Meeting summary here.",
        )
        
        assert data.company_name is None
        assert data.attendees == []
        assert data.action_items == []


class TestWebhookEndpoint:
    """Tests for webhook endpoint."""
    
    def test_webhook_accepts_valid_payload(self):
        """Webhook returns 200 for valid payload."""
        with patch('app.routers.webhook.get_db') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            
            response = client.post(
                "/webhook/fathom",
                json=SAMPLE_PAYLOAD,
                headers={"webhook-signature": "v1,test"}
            )
            
            # Should accept (processing happens in background)
            assert response.status_code == 200
    
    def test_webhook_rejects_invalid_json(self):
        """Webhook returns 400 for invalid JSON."""
        response = client.post(
            "/webhook/fathom",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]


class TestAIProcessorMock:
    """Tests for AI processor with mocked API."""
    
    @pytest.mark.asyncio
    async def test_extract_meeting_data(self):
        """AI extraction returns structured data."""
        from app.services.ai_processor import extract_meeting_data
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "company_name": "Acme Corp",
                        "company_domain": "acme.com",
                        "attendees": ["John", "Sarah"],
                        "crm_note": "Discussed implementation.",
                        "action_items": ["Send SOW"],
                        "meeting_sentiment": "positive",
                        "deal_stage_signal": "negotiation",
                        "key_topics": ["implementation"]
                    })
                }
            }]
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            result = await extract_meeting_data(
                transcript="Test transcript",
                meeting_title="Test Meeting"
            )
            
            assert result.company_name == "Acme Corp"
            assert result.crm_note == "Discussed implementation."


class TestHubSpotServiceMock:
    """Tests for HubSpot service with mocked API."""
    
    @pytest.mark.asyncio
    async def test_search_company_by_domain(self):
        """Company search by domain returns result."""
        from app.services.hubspot import HubSpotClient
        
        mock_response = {
            "results": [{
                "id": "12345",
                "properties": {
                    "name": "Acme Corporation",
                    "domain": "acme.com"
                }
            }]
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            client = HubSpotClient("test_token")
            result = await client.search_company_by_domain("acme.com")
            
            assert result is not None
            assert result.id == "12345"
            assert result.name == "Acme Corporation"
    
    @pytest.mark.asyncio
    async def test_search_company_not_found(self):
        """Company search returns None when not found."""
        from app.services.hubspot import HubSpotClient
        
        mock_response = {"results": []}
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            client = HubSpotClient("test_token")
            result = await client.search_company_by_domain("unknown.com")
            
            assert result is None


# Run with: pytest tests/test_webhook.py -v
