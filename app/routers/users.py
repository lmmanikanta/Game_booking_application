from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, join
from app.database import get_db
from app.models import models
from app.schemas import users as user_schemas
from app.auth.auth_handler import get_password_hash, create_access_token, verify_password, get_current_user
from datetime import timedelta
from typing import List

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"}
    }
)

@router.post("/register", response_model=user_schemas.User)
async def register_user(user: user_schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # Create a query to check for existing user
    query = select(models.User).where(
        or_(
            models.User.email == user.email,
            models.User.sap_id == user.sap_id
        )
    )
    result = await db.execute(query)
    if result.first():
        raise HTTPException(status_code=400, detail="Email or SAP ID already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        sap_id=user.sap_id,
        hashed_password=hashed_password,
        role="user"
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post(
    "/login", 
    response_model=user_schemas.Token,
    summary="Login to get access token",
    description="Login with email/SAP ID and password to get JWT token for authentication",
    responses={
        200: {
            "description": "Successful login",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {"description": "Invalid credentials"}
    }
)
async def login(user: user_schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    # Check if the username is an email or SAP ID
    query = select(models.User).where(
        or_(
            models.User.email == user.username,
            models.User.sap_id == user.username
        )
    )
    result = await db.execute(query)
    user_data = result.first()
    
    if not user_data or not verify_password(user.password, user_data[0].hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email, SAP ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user_data[0].email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=user_schemas.User)
async def get_current_user_info(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(models.User).where(models.User.email == current_user)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/bookings/history", response_model=List[user_schemas.BookingHistory])
async def get_user_booking_history(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Create a query to get booking history using joins
    query = (
        select(
            models.Booking,
            models.Slot.start_time,
            models.Slot.end_time,
            models.Game.name.label('game_name')
        )
        .join(models.Slot, models.Booking.slot_id == models.Slot.id)
        .join(models.Game, models.Slot.game_id == models.Game.id)
        .join(models.User, models.Booking.user_id == models.User.id)
        .where(
            (models.User.email == current_user) &
            (models.Booking.status != 'cancelled')
        )
        .order_by(models.Booking.created_at.desc())
    )
    
    result = await db.execute(query)
    bookings = result.fetchall()
    return [
        {
            **booking[0].__dict__,
            'start_time': booking[1],
            'end_time': booking[2],
            'game_name': booking[3]
        }
        for booking in bookings
    ]