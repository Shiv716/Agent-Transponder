"""
Agent Transponder - FastAPI Application

Automated meeting-to-CRM pipeline with AI-powered follow-up notes.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.routers import webhook, meetings
from app.models.schemas import HealthResponse


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    
    # Startup
    logger.info(f"Starting {settings.app_name}...")
    logger.info(f"Environment: {settings.app_env}")
    
    # Initialize database tables
    await init_db()
    
    logger.info("✅ Application ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create application
app = FastAPI(
    title=settings.app_name,
    description="Automated meeting-to-CRM pipeline with AI-powered follow-up notes.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(webhook.router)
app.include_router(meetings.router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with basic info."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.app_env != "production" else "disabled",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )
