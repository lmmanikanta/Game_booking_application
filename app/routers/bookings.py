from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update, insert
from app.database import get_db
from app.models import models
from app.schemas import games as game_schemas
from app.auth.auth_handler import get_current_user
from typing import List
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/bookings",
    tags=["bookings"]
)

@router.post("/", response_model=game_schemas.Booking)
async def create_booking(
    booking: game_schemas.BookingCreate,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get user details
    user_query = select(models.User).where(models.User.email == current_user)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get slot details with game information
    slot_query = (
        select(
            models.Slot,
            models.Game.type.label('game_type'),
            models.Game.max_players
        )
        .join(models.Game)
        .where(models.Slot.id == booking.slot_id)
    )
    result = await db.execute(slot_query)
    slot_data = result.first()
    if not slot_data:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot, game_type, max_players = slot_data
    
    if not slot.is_available or slot.is_cancelled:
        raise HTTPException(status_code=400, detail="Slot is not available")

    # Check if user has already booked same game twice today
    today_bookings_query = (
        select(func.count())
        .select_from(models.Booking)
        .join(models.Slot)
        .join(models.Game)
        .where(
            and_(
                models.Booking.user_id == user.id,
                models.Game.type == game_type,
                func.date(models.Slot.start_time) == datetime.utcnow().date(),
                models.Booking.status != 'cancelled'
            )
        )
    )
    result = await db.execute(today_bookings_query)
    booking_count = result.scalar()
    if booking_count >= 2:
        raise HTTPException(
            status_code=400,
            detail=f"You have already booked {game_type} twice today"
        )

    # Validate other players if provided
    if booking.other_players:
        other_players_list = booking.other_players.split(",")
        if len(other_players_list) > max_players - 1:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {max_players} players allowed for this game"
            )
        
        # Verify other players exist
        other_players_query = (
            select(func.count())
            .select_from(models.User)
            .where(models.User.sap_id.in_(other_players_list))
        )
        result = await db.execute(other_players_query)
        valid_players_count = result.scalar()
        if valid_players_count != len(other_players_list):
            raise HTTPException(status_code=400, detail="One or more player SAP IDs are invalid")

    # Create booking
    now = datetime.utcnow()
    new_booking_stmt = insert(models.Booking).values(
        user_id=user.id,
        slot_id=booking.slot_id,
        other_players=booking.other_players,
        status='pending',
        created_at=now,
        updated_at=now
    ).returning(models.Booking)
    
    result = await db.execute(new_booking_stmt)
    new_booking = result.scalar_one()

    # Update slot availability
    update_stmt = (
        update(models.Slot)
        .where(models.Slot.id == booking.slot_id)
        .values(is_available=False)
    )
    await db.execute(update_stmt)

    await db.commit()
    return new_booking

@router.post("/{booking_id}/check-in")
async def check_in(
    booking_id: int,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get booking details
    booking_result = await db.execute(
        """
        SELECT b.*, s.start_time, u.email
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN users u ON b.user_id = u.id
        WHERE b.id = :booking_id
        """,
        {"booking_id": booking_id}
    )
    booking = booking_result.first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.email != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to check in for this booking")

    now = datetime.utcnow()
    start_time = booking.start_time

    # Check if it's too early or too late to check in
    if now < start_time - timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Too early to check in")
    
    if now > start_time + timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Check-in period has expired")

    # Update booking status
    await db.execute(
        """
        UPDATE bookings 
        SET checked_in = true,
            check_in_time = :check_in_time,
            status = 'confirmed',
            updated_at = :updated_at
        WHERE id = :booking_id
        """,
        {
            "booking_id": booking_id,
            "check_in_time": now,
            "updated_at": now
        }
    )

    await db.commit()
    return {"message": "Successfully checked in"}


@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: int,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a booking. Allowed for booking owner or admin."""
    # Fetch booking, slot and owner
    stmt = (
        select(models.Booking, models.Slot, models.User)
        .join(models.Slot, models.Booking.slot_id == models.Slot.id)
        .join(models.User, models.Booking.user_id == models.User.id)
        .where(models.Booking.id == booking_id)
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking_obj, slot_obj, owner = row[0], row[1], row[2]

    # Get caller details
    user_q = select(models.User).where(models.User.email == current_user)
    user_res = await db.execute(user_q)
    caller = user_res.scalar_one_or_none()
    if not caller:
        raise HTTPException(status_code=404, detail="User not found")

    # Permission: owner or admin
    if caller.role != 'admin' and owner.email != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    if booking_obj.status == 'cancelled':
        raise HTTPException(status_code=400, detail='Booking already cancelled')

    now = datetime.utcnow()

    # Update booking status to cancelled
    await db.execute(
        update(models.Booking)
        .where(models.Booking.id == booking_id)
        .values(status='cancelled', updated_at=now)
    )

    # Mark slot available again if not cancelled
    await db.execute(
        update(models.Slot)
        .where(models.Slot.id == slot_obj.id)
        .where(models.Slot.is_cancelled == False)
        .values(is_available=True, updated_at=now)
    )

    await db.commit()
    return {"message": "Booking cancelled successfully"}