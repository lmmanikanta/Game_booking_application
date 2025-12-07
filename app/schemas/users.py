from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from app.models.models import GameType, GameStatus, UserRole

class PasswordMixin:
    @validator('password')
    def validate_password(cls, v):
        # Validate password length and complexity
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot be longer than 72 bytes')
        # Add more password complexity requirements here if needed
        return v

class UserBase(BaseModel):
    email: EmailStr
    sap_id: str

    @validator('sap_id')
    def validate_sap_id(cls, v):
        if not v.strip():
            raise ValueError('SAP ID cannot be empty')
        return v

class UserCreate(UserBase, PasswordMixin):
    password: str

class UserLogin(PasswordMixin, BaseModel):
    username: str  # This can be either email or SAP ID
    password: str

class User(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class BookingHistory(BaseModel):
    id: int
    game_name: str
    start_time: datetime
    end_time: datetime
    status: str
    other_players: Optional[str]
    checked_in: bool
    check_in_time: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True