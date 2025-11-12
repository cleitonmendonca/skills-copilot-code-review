"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    start_date: Optional[datetime] = None
    expiration_date: datetime
    is_active: bool = True


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    message: Optional[str] = Field(None, min_length=1, max_length=1000)
    start_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    is_active: Optional[bool] = None


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements(
    active_only: bool = Query(default=True, description="Return only active announcements"),
    teacher_username: Optional[str] = Query(None)
) -> List[Dict[str, Any]]:
    """
    Get all announcements. If active_only=True, returns only announcements that are currently active
    based on start_date and expiration_date. Requires teacher authentication for management access.
    """
    # Build the query based on active_only flag and current date
    query = {}
    
    if active_only:
        current_time = datetime.now()
        query = {
            "is_active": True,
            "$and": [
                {"expiration_date": {"$gte": current_time}},
                {"$or": [
                    {"start_date": {"$lte": current_time}},
                    {"start_date": None}
                ]}
            ]
        }

    # For management access (getting all announcements), verify teacher authentication
    if not active_only and teacher_username:
        teacher = teachers_collection.find_one({"_id": teacher_username})
        if not teacher:
            raise HTTPException(
                status_code=401, detail="Authentication required for management access")

    announcements = []
    for announcement in announcements_collection.find(query).sort("created_at", -1):
        # Convert ObjectId to string for JSON serialization
        announcement["id"] = str(announcement.pop("_id"))
        # Convert datetime objects to ISO format strings for frontend
        for field in ["start_date", "expiration_date", "created_at"]:
            if field in announcement and announcement[field]:
                announcement[field] = announcement[field].isoformat()
        announcements.append(announcement)

    return announcements


@router.post("", response_model=Dict[str, str])
@router.post("/", response_model=Dict[str, str])
def create_announcement(
    announcement: AnnouncementCreate,
    teacher_username: str = Query(..., description="Username of the authenticated teacher")
) -> Dict[str, str]:
    """Create a new announcement - requires teacher authentication"""
    # Verify teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    # Validate expiration date is in the future
    if announcement.expiration_date <= datetime.now():
        raise HTTPException(
            status_code=400, detail="Expiration date must be in the future")

    # Validate start date is before expiration date if provided
    if announcement.start_date and announcement.start_date >= announcement.expiration_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before expiration date")

    # Create announcement document
    announcement_doc = {
        "title": announcement.title,
        "message": announcement.message,
        "start_date": announcement.start_date,
        "expiration_date": announcement.expiration_date,
        "created_by": teacher_username,
        "created_at": datetime.now(),
        "is_active": announcement.is_active
    }

    # Insert into database
    result = announcements_collection.insert_one(announcement_doc)

    if not result.inserted_id:
        raise HTTPException(
            status_code=500, detail="Failed to create announcement")

    return {"message": f"Announcement '{announcement.title}' created successfully", "id": str(result.inserted_id)}


@router.put("/{announcement_id}", response_model=Dict[str, str])
def update_announcement(
    announcement_id: str,
    announcement: AnnouncementUpdate,
    teacher_username: str = Query(..., description="Username of the authenticated teacher")
) -> Dict[str, str]:
    """Update an existing announcement - requires teacher authentication"""
    # Verify teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    # Check if announcement exists
    from bson import ObjectId
    try:
        existing = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Build update document with only provided fields
    update_doc = {}
    if announcement.title is not None:
        update_doc["title"] = announcement.title
    if announcement.message is not None:
        update_doc["message"] = announcement.message
    if announcement.start_date is not None:
        update_doc["start_date"] = announcement.start_date
    if announcement.expiration_date is not None:
        update_doc["expiration_date"] = announcement.expiration_date
    if announcement.is_active is not None:
        update_doc["is_active"] = announcement.is_active

    # Validate dates if provided
    final_expiration = announcement.expiration_date if announcement.expiration_date is not None else existing["expiration_date"]
    final_start = announcement.start_date if announcement.start_date is not None else existing.get("start_date")

    if final_expiration and final_expiration <= datetime.now():
        raise HTTPException(
            status_code=400, detail="Expiration date must be in the future")

    if final_start and final_start >= final_expiration:
        raise HTTPException(
            status_code=400, detail="Start date must be before expiration date")

    if not update_doc:
        raise HTTPException(
            status_code=400, detail="No fields provided for update")

    # Update the announcement
    result = announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_doc}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=500, detail="Failed to update announcement")

    return {"message": "Announcement updated successfully"}


@router.delete("/{announcement_id}", response_model=Dict[str, str])
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(..., description="Username of the authenticated teacher")
) -> Dict[str, str]:
    """Delete an announcement - requires teacher authentication"""
    # Verify teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    # Check if announcement exists and delete
    from bson import ObjectId
    try:
        result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted successfully"}