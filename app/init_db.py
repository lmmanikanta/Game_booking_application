from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base, User, Game, GameType, GameStatus
from app.auth.auth_handler import get_password_hash
from datetime import datetime, timedelta

# Create database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./game_booking.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Create admin user
admin_user = User(
    email="admin@company.com",
    sap_id="123456789",
    hashed_password=get_password_hash("Admin@2025"),
    role="admin"
)

# Create test user
test_user = User(
    email="user@company.com",
    sap_id="USER001",
    hashed_password=get_password_hash("user123"),
    role="user"
)

# Create games
games = [
    Game(
        name="Chess Board 1",
        type=GameType.CHESS,
        max_players=2,
        status=GameStatus.ACTIVE
    ),
    Game(
        name="Carrom Board 1",
        type=GameType.CARROM,
        max_players=4,
        status=GameStatus.ACTIVE
    ),
    Game(
        name="Table Tennis 1",
        type=GameType.TABLE_TENNIS,
        max_players=4,
        status=GameStatus.ACTIVE
    ),
    Game(
        name="Badminton Court 1",
        type=GameType.BADMINTON,
        max_players=4,
        status=GameStatus.ACTIVE
    ),
    Game(
        name="Fuss Ball Table 1",
        type=GameType.FUSS_BALL,
        max_players=2,
        status=GameStatus.ACTIVE
    )
]

try:
    # Add users
    db.add(admin_user)
    db.add(test_user)
    
    # Add games
    for game in games:
        db.add(game)
    
    db.commit()
    print("Successfully added initial data!")

except Exception as e:
    print(f"Error adding initial data: {e}")
    db.rollback()

finally:
    db.close()