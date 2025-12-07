from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, join
from app.database import get_db
from app.models import models
from app.schemas import games as game_schemas
from app.auth.auth_handler import get_current_user
from typing import List
from datetime import datetime, timedelta, time

router = APIRouter(
    prefix="/slots",
    tags=["slots"]
)

@router.get("/{slot_id}", response_model=game_schemas.Slot)
async def get_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_db)
):
    query = select(models.Slot).where(models.Slot.id == slot_id)
    result = await db.execute(query)
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return slot

@router.get("/available/{date}", response_model=List[game_schemas.Slot])
async def get_available_slots(
    date: str,
    game_type: str = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Check if it's weekend
    if selected_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        raise HTTPException(status_code=400, detail="No slots available on weekends")

    # Build the query using SQLAlchemy expressions
    query = (
        select(models.Slot)
        .join(models.Game)
        .where(
            and_(
                func.date(models.Slot.start_time) == selected_date.date(),
                func.time(models.Slot.start_time) >= time(9, 0),
                func.time(models.Slot.start_time) <= time(20, 0),
                models.Slot.is_available == True,
                models.Slot.is_cancelled == False,
                models.Game.status == 'active'
            )
        )
    )

    if game_type:
        query = query.where(models.Game.type == game_type)

    query = query.order_by(models.Slot.start_time)
    
    result = await db.execute(query)
    slots = result.scalars().all()
    return slots

@router.get("/game/{game_id}/date/{date}", response_model=List[game_schemas.Slot])
async def get_game_slots_by_date(
    game_id: int,
    date: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Check if it's weekend
    if selected_date.weekday() >= 5:
        raise HTTPException(status_code=400, detail="No slots available on weekends")

    query = (
        select(models.Slot)
        .join(models.Game)
        .where(
            and_(
                models.Slot.game_id == game_id,
                func.date(models.Slot.start_time) == selected_date.date(),
                func.time(models.Slot.start_time) >= time(9, 0),
                func.time(models.Slot.start_time) <= time(20, 0),
                models.Slot.is_cancelled == False,
                models.Game.status == 'active'
            )
        )
        .order_by(models.Slot.start_time)
    )
    
    result = await db.execute(query)
    slots = result.scalars().all()
    return slots