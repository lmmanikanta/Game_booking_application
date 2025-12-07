from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel # <--- Import BaseModel
from app.database import get_db
from app.models import models
from app.schemas import games as game_schemas
from app.auth.auth_handler import get_current_user
from typing import List
from datetime import datetime, timedelta, time
import asyncio

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# --- NEW: Define a Pydantic model for the request body ---
class GameStatusUpdateRequest(BaseModel):
    status: models.GameStatus

async def verify_admin(current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Use SQLAlchemy select expression
    query = select(models.User.role).where(models.User.email == current_user)
    result = await db.execute(query)
    user_role = result.scalar_one_or_none()
    
    if not user_role or user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

@router.post("/games", response_model=game_schemas.Game)
async def create_game(
    game: game_schemas.GameCreate,
    admin: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.utcnow()
    new_game = models.Game(
        name=game.name,
        type=game.type,
        max_players=game.max_players,
        status=models.GameStatus.ACTIVE,
        created_at=now,
        updated_at=now
    )
    db.add(new_game)
    await db.commit()
    await db.refresh(new_game)
    return new_game

# --- MODIFIED ENDPOINT ---
@router.put("/games/{game_id}/status", response_model=game_schemas.Game)
async def update_game_status(
    game_id: int,
    payload: GameStatusUpdateRequest, # <--- CHANGED: Use the Pydantic model here
    admin: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.utcnow()

    # Get the game using a write lock
    stmt = (
        select(models.Game)
        .where(models.Game.id == game_id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Update the game's status from the payload
    game.status = payload.status # <--- CHANGED: Get status from payload
    game.updated_at = now

    # If game is inactive, cancel all future slots
    if payload.status == models.GameStatus.INACTIVE: # <--- CHANGED: Check status from payload
        # Get all future slots for this game
        future_slots_stmt = (
            select(models.Slot)
            .where(
                (models.Slot.game_id == game_id) &
                (models.Slot.start_time > now)
            )
        )
        result = await db.execute(future_slots_stmt)
        future_slots = result.scalars().all()

        # Update slots and their bookings
        for slot in future_slots:
            slot.is_cancelled = True
            slot.cancellation_reason = 'Game temporarily unavailable'
            slot.updated_at = now

            # Update associated bookings
            bookings_stmt = (
                select(models.Booking)
                .where(
                    (models.Booking.slot_id == slot.id) &
                    (models.Booking.status == 'pending')
                )
            )
            result = await db.execute(bookings_stmt)
            bookings = result.scalars().all()

            for booking in bookings:
                booking.status = 'cancelled'
                booking.updated_at = now

    await db.commit()
    await db.refresh(game) # Refresh the object to get the updated state from the DB
    
    return game # Return the updated game object

# ... (rest of your admin.py file is unchanged) ...

class SlotGenerateRequest(BaseModel):
    game_id: int
    date: str

@router.post("/slots/generate")
async def generate_slots(
    request: SlotGenerateRequest,
    admin: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        selected_date = datetime.strptime(request.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if selected_date.weekday() >= 5:
        raise HTTPException(status_code=400, detail="Cannot generate slots for weekends")

    stmt = select(models.Game).where(models.Game.id == request.game_id)
    result = await db.execute(stmt)
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status != models.GameStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot generate slots for inactive game")

    slots = []
    start_hour = 9
    end_hour = 20
    current = selected_date.replace(hour=start_hour, minute=0)
    end_time = selected_date.replace(hour=end_hour, minute=0)

    while current < end_time:
        slot_end = current + timedelta(minutes=30)
        new_slot = models.Slot(
            game_id=request.game_id,
            start_time=current,
            end_time=slot_end,
            is_available=True,
            is_cancelled=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        slots.append(new_slot)
        current = slot_end

    db.add_all(slots)
    await db.commit()

    return {"message": f"Generated {len(slots)} slots for {request.date}"}

@router.delete("/slots/cancel")
async def cancel_slots(
    game_id: int,
    date: str,
    reason: str,
    admin: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    now = datetime.utcnow()

    stmt = (
        select(models.Slot)
        .where(
            (models.Slot.game_id == game_id) &
            (func.date(models.Slot.start_time) == selected_date.date())
        )
    )
    result = await db.execute(stmt)
    slots = result.scalars().all()

    for slot in slots:
        slot.is_cancelled = True
        slot.is_available = False
        slot.cancellation_reason = reason
        slot.updated_at = now

        booking_stmt = (
            select(models.Booking)
            .where(
                (models.Booking.slot_id == slot.id) &
                (models.Booking.status == 'pending')
            )
        )
        result = await db.execute(booking_stmt)
        bookings = result.scalars().all()

        for booking in bookings:
            booking.status = 'cancelled'
            booking.updated_at = now

    await db.commit()
    return {"message": f"Cancelled all slots for game {game_id} on {date}"}