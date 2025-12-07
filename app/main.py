from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime, timedelta
import asyncio
from typing import List
from app.database import get_db, engine, Base
from app.models import models
from app.auth.auth_handler import get_current_user
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(
    title="Game Booking System",
    description="API for managing game slot bookings",
    version="1.0.0",
    openapi_tags=[
        {"name": "users", "description": "User operations including authentication"},
        {"name": "games", "description": "Game management operations"},
        {"name": "slots", "description": "Slot booking and management"},
        {"name": "bookings", "description": "Booking operations"},
        {"name": "admin", "description": "Admin only operations"},
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "persistAuthorization": True
    }
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Background task for checking and releasing slots
async def check_and_release_slots():
    while True:
        try:
            async with AsyncSession(engine) as session:
                current_time = datetime.utcnow()
                check_time = current_time + timedelta(minutes=5)
                
                # Get all pending bookings where start time is within next 5 minutes
                query = (
                    select(
                        models.Booking.id,
                        models.Booking.user_id,
                        models.Slot.start_time,
                        models.User.email
                    )
                    .join(models.Slot, models.Booking.slot_id == models.Slot.id)
                    .join(models.User, models.Booking.user_id == models.User.id)
                    .where(
                        and_(
                            models.Booking.status == 'pending',
                            models.Slot.start_time <= check_time,
                            models.Booking.checked_in == False
                        )
                    )
                )
                
                result = await session.execute(query)
                bookings_to_cancel = result.fetchall()

                for booking in bookings_to_cancel:
                    # Cancel booking
                    update_stmt = (
                        update(models.Booking)
                        .where(models.Booking.id == booking.id)
                        .values(
                            status='cancelled',
                            updated_at=current_time
                        )
                    )
                    await session.execute(update_stmt)
                    
                    # Send email notification
                    send_email(
                        booking.email,
                        "Booking Cancelled - No Check-in",
                        "Your booking has been cancelled due to no check-in within 5 minutes of start time."
                    )
                await session.commit()
        except Exception as e:
            print(f"Error in slot checking task: {e}")
        await asyncio.sleep(60)  # Check every minute

@app.on_event("startup")
async def start_slot_checker():
    asyncio.create_task(check_and_release_slots())

# Email sending function
def send_email(to_email: str, subject: str, body: str):
    # Configure your email settings here
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-email@gmail.com"
    sender_password = "your-app-password"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
    except Exception as e:
        print(f"Failed to send email: {e}")

# Import and include routers
from app.routers import users, games, slots, bookings, admin

app.include_router(users.router)
app.include_router(games.router)
app.include_router(slots.router)
app.include_router(bookings.router)
app.include_router(admin.router)