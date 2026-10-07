from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, Optional

from services.webapp_auth import get_current_webapp_user
from database import db_manager

router = APIRouter(prefix="/api/v1/webapp", tags=["webapp"])

@router.get("/market")
async def get_market_items(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    user: Dict[str, Any] = Depends(get_current_webapp_user)
):
    """
    دریافت آیتم‌های بازارچه برای نمایش در مینی‌اپ
    """
    items = await db_manager.get_market_items(limit=limit, skip=skip)
    return {"items": items, "user_id": user.get("id")}

@router.get("/roommates")
async def get_roommates(
    area: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_webapp_user)
):
    """
    دریافت آگهی‌های هم‌اتاقی برای نمایش در مینی‌اپ
    """
    ads = await db_manager.get_active_roommate_ads(area=area, limit=limit)
    return {"ads": ads, "user_id": user.get("id")}

@router.get("/events")
async def get_events(
    user: Dict[str, Any] = Depends(get_current_webapp_user)
):
    """
    دریافت رویدادهای دانشجویی برای نمایش در مینی‌اپ
    """
    events = await db_manager.get_events()
    return {"events": events, "user_id": user.get("id")}

@router.get("/me")
async def get_me(user: Dict[str, Any] = Depends(get_current_webapp_user)):
    """
    مسیر تستی برای چک کردن صحت توکن کاربر تلگرام
    """
    profile = await db_manager.get_user(user.get("id", 0))
    return {"user": user, "profile": profile, "status": "authenticated"}

