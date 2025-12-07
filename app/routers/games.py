from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from app.database import get_db
from app.models import models
from app.schemas import games as game_schemas
from app.auth.auth_handler import get_current_user
from typing import List
from datetime import datetime, time

router = APIRouter(
    prefix="/games",
    tags=["games"]
)

@router.get("/", response_model=List[game_schemas.Game])
async def get_all_games(db: AsyncSession = Depends(get_db)):
    query = select(models.Game)
    result = await db.execute(query)
    games = result.scalars().all()
    return games

@router.get("/{game_id}/slots", response_model=List[game_schemas.Slot])
async def get_game_slots(
    game_id: int,
    date: str,
    db: AsyncSession = Depends(get_db)
):
    # Convert date string to datetime
    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Check if it's weekend
    if selected_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        raise HTTPException(status_code=400, detail="No slots available on weekends")

    # Get slots for the specific date between 9 AM and 8 PM
    query = (
        select(models.Slot)
        .where(
            and_(
                models.Slot.game_id == game_id,
                func.date(models.Slot.start_time) == selected_date.date(),
                func.time(models.Slot.start_time).between(time(9, 0), time(20, 0)),
                models.Slot.is_cancelled == False
            )
        )
        .order_by(models.Slot.start_time)
    )
    
    result = await db.execute(query)
    slots = result.scalars().all()
    return slots

@router.get("/{game_id}", response_model=game_schemas.Game)
async def get_game(game_id: int, db: AsyncSession = Depends(get_db)):
    query = select(models.Game).where(models.Game.id == game_id)
    result = await db.execute(query)
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game