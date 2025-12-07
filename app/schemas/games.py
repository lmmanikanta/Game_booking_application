from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.models import GameType, GameStatus

class GameBase(BaseModel):
    name: str
    type: GameType
    max_players: int

class GameCreate(GameBase):
    pass

class Game(GameBase):
    id: int
    status: GameStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class SlotBase(BaseModel):
    game_id: int
    start_time: datetime
    end_time: datetime

class SlotCreate(SlotBase):
    pass

class Slot(SlotBase):
    id: int
    is_available: bool
    is_cancelled: bool
    cancellation_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class BookingBase(BaseModel):
    slot_id: int
    other_players: Optional[str]

class BookingCreate(BookingBase):
    pass

class Booking(BookingBase):
    id: int
    user_id: int
    status: str
    checked_in: bool
    check_in_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True