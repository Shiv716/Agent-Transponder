"""
Application configuration loaded from environment variables.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable loading."""
    
    # Application
    app_name: str = "Agent Transponder"
    app_env: str = "development"
    debug: bool = False
    
    # Database
    database_url: str
    
    # Fathom
    fathom_webhook_secret: str
    
    # HubSpot
    hubspot_access_token: str
    
    # Groq (LLM)
    groq_api_key: str
    groq_model: str = "llama-3.1-70b-versatile"

    # OpenAI (LLM)
    openai_api_key: str
    openai_model: str = "gpt-4"
    
    # Resend (Email)
    resend_api_key: str
    email_from: str = "Agent Transponder <noreply@yourdomain.com>"
    
    # User Configuration (single demo account)
    user_email: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
