
import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker


# ============================================================
# DATABASE CONFIGURATION - AIVEN / RENDER
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is missing"
    )

# Convert standard MySQL URL to PyMySQL URL if necessary.
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "mysql://",
        "mysql+pymysql://",
        1,
    )

# Remove query parameters such as ssl-mode=REQUIRED.
# SSL is configured separately below for Aiven.
if "?" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?", 1)[0]


# ============================================================
# CREATE DATABASE ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"ssl": {}},
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# BASE CLASS
# ============================================================

Base = declarative_base()


# ============================================================
# USER TABLE
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(String(255), nullable=False)


# ============================================================
# SONG TABLE
# ============================================================

class Song(Base):
    __tablename__ = "songs"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    track_id = Column(
        String(100),
        unique=True,
        nullable=False,
    )

    track_name = Column(String(255), nullable=False)
    track_artist = Column(String(255))
    genre = Column(String(100))
    subgenre = Column(String(100))
    mood = Column(String(50))

    danceability = Column(Float)
    energy = Column(Float)
    acousticness = Column(Float)
    instrumentalness = Column(Float)
    valence = Column(Float)
    tempo = Column(Float)
    popularity = Column(Integer)


# ============================================================
# LISTENING HISTORY TABLE
# ============================================================

class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id = Column(Integer, nullable=False)
    song_id = Column(String(100), nullable=False)

    played_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    completion_percentage = Column(Float, default=0)
    completed = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    liked = Column(Boolean, default=False)


# ============================================================
# LIKES TABLE
# ============================================================

class Like(Base):
    __tablename__ = "likes"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id = Column(Integer, nullable=False)
    song_id = Column(String(100), nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# CREATE MISSING TABLES
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# DATABASE CONNECTION FUNCTION
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
