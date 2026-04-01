"""
HubSpot API integration service.

Handles company search and note creation.
"""

import logging
from datetime import datetime
from typing import Optional, List
import httpx

from app.core.config import settings
from app.models.schemas import HubSpotCompany

logger = logging.getLogger(__name__)

# HubSpot API base URL
HUBSPOT_API_URL = "https://api.hubapi.com"


class HubSpotClient:
    """HubSpot API client."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
    async def search_company_by_domain(self, domain: str) -> Optional[HubSpotCompany]:
        """
        Search for a company by domain.
        
        Args:
            domain: Company website domain (e.g., "acme.com")
        
        Returns:
            HubSpotCompany if found, None otherwise
        """
        
        # Clean domain
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        
        url = f"{HUBSPOT_API_URL}/crm/v3/objects/companies/search"
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "domain",
                            "operator": "CONTAINS_TOKEN",
                            "value": domain,
                        }
                    ]
                }
            ],
            "properties": ["name", "domain", "website", "industry"],
            "limit": 1,
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                
                if results:
                    company = results[0]
                    logger.info(f"Found company by domain '{domain}': {company['properties'].get('name')}")
                    return HubSpotCompany(
                        id=company["id"],
                        name=company["properties"].get("name", "Unknown"),
                        domain=company["properties"].get("domain"),
                        properties=company["properties"],
                    )
                
                logger.info(f"No company found for domain: {domain}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HubSpot search error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error searching HubSpot: {e}")
            return None
    
    async def search_company_by_name(self, name: str) -> Optional[HubSpotCompany]:
        """
        Search for a company by name.
        
        Args:
            name: Company name to search
        
        Returns:
            HubSpotCompany if found, None otherwise
        """
        
        url = f"{HUBSPOT_API_URL}/crm/v3/objects/companies/search"
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "name",
                            "operator": "CONTAINS_TOKEN",
                            "value": name,
                        }
                    ]
                }
            ],
            "properties": ["name", "domain", "website", "industry"],
            "limit": 3,
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                
                if results:
                    # Return best match (first result)
                    company = results[0]
                    logger.info(f"Found company by name '{name}': {company['properties'].get('name')}")
                    return HubSpotCompany(
                        id=company["id"],
                        name=company["properties"].get("name", "Unknown"),
                        domain=company["properties"].get("domain"),
                        properties=company["properties"],
                    )
                
                logger.info(f"No company found for name: {name}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HubSpot search error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error searching HubSpot: {e}")
            return None
    
    async def find_company(
        self, 
        company_name: Optional[str] = None, 
        company_domain: Optional[str] = None
    ) -> Optional[HubSpotCompany]:
        """
        Find a company by domain (preferred) or name.
        
        Args:
            company_name: Company name to search
            company_domain: Company domain to search (preferred)
        
        Returns:
            HubSpotCompany if found
        """
        
        # Try domain first (more reliable)
        if company_domain:
            company = await self.search_company_by_domain(company_domain)
            if company:
                return company
        
        # Fall back to name search
        if company_name:
            company = await self.search_company_by_name(company_name)
            if company:
                return company
        
        return None
    
    async def create_note(
        self,
        company_id: str,
        note_body: str,
        timestamp: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Create a note (engagement) associated with a company.
        
        Args:
            company_id: HubSpot company ID
            note_body: Note content (supports HTML)
            timestamp: Optional timestamp for the note
        
        Returns:
            Note ID if created successfully
        """
        
        url = f"{HUBSPOT_API_URL}/crm/v3/objects/notes"
        
        # Format timestamp
        ts = timestamp or datetime.utcnow()
        ts_ms = int(ts.timestamp() * 1000)
        
        payload = {
            "properties": {
                "hs_timestamp": str(ts_ms),
                "hs_note_body": note_body,
            },
            "associations": [
                {
                    "to": {"id": company_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 190,  # Note to Company
                        }
                    ],
                }
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                note_id = data.get("id")
                
                logger.info(f"Created HubSpot note {note_id} for company {company_id}")
                return note_id
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HubSpot note creation error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating HubSpot note: {e}")
            return None
    
    def get_company_url(self, company_id: str) -> str:
        """Generate HubSpot company record URL."""
        return f"https://app.hubspot.com/contacts/148137078/company/{company_id}"


# Default client instance
def get_hubspot_client() -> HubSpotClient:
    """Get HubSpot client with configured access token."""
    return HubSpotClient(settings.hubspot_access_token)
