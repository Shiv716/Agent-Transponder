"""
Meeting history and management endpoints.
"""

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db, Meeting
from app.models.schemas import MeetingResponse, MeetingListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=MeetingListResponse)
async def list_meetings(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List processed meetings, most recent first.
    """
    
    # Get total count
    count_result = await db.execute(select(Meeting))
    total = len(count_result.scalars().all())
    
    # Get paginated results
    result = await db.execute(
        select(Meeting)
        .order_by(desc(Meeting.created_at))
        .offset(offset)
        .limit(limit)
    )
    meetings = result.scalars().all()
    
    return MeetingListResponse(
        meetings=[MeetingResponse.model_validate(m) for m in meetings],
        total=total,
    )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific meeting.
    """
    
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    return MeetingResponse.model_validate(meeting)


@router.get("/by-fathom/{recording_id}", response_model=MeetingResponse)
async def get_meeting_by_fathom_id(
    recording_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get meeting by Fathom recording ID.
    """
    
    result = await db.execute(
        select(Meeting).where(Meeting.fathom_recording_id == recording_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    return MeetingResponse.model_validate(meeting)


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a meeting record.
    
    Note: This does not delete the HubSpot note or Fathom recording.
    """
    
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    await db.delete(meeting)
    await db.commit()
    
    return {"status": "deleted", "meeting_id": str(meeting_id)}
