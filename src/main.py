
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db, Song, ListeningHistory, Like
from src.recommendation_engine import recommend
from src.youtube_service import find_youtube_video

app = FastAPI(
    title="TuneSense AI Music Recommendation System",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TrackAction(BaseModel):
    user_id: int
    track_id: str


def song_to_dict(song):
    return {
        "track_id": song.track_id,
        "track_name": song.track_name,
        "track_artist": song.track_artist,
        "genre": song.genre,
        "subgenre": song.subgenre,
        "mood": song.mood,
        "popularity": song.popularity
    }


def find_song(db: Session, name: str):
    return db.query(Song).filter(
        func.lower(func.trim(Song.track_name)) ==
        name.strip().lower()
    ).first()


@app.get("/")
def home():
    return {
        "message": "TuneSense API is running!",
        "status": "success"
    }


@app.get("/songs")
def get_songs(db: Session = Depends(get_db)):
    songs = db.query(Song).limit(100).all()
    return [song_to_dict(song) for song in songs]


@app.get("/search")
def search_songs(
    query: str,
    db: Session = Depends(get_db)
):
    songs = db.query(Song).filter(
        Song.track_name.like(f"%{query}%") |
        Song.track_artist.like(f"%{query}%")
    ).limit(50).all()

    return [song_to_dict(song) for song in songs]


@app.post("/history")
def save_history(
    action: TrackAction,
    db: Session = Depends(get_db)
):
    history = ListeningHistory(
        user_id=action.user_id,
        song_id=action.track_id,
        completion_percentage=0,
        completed=False,
        skipped=False,
        liked=False
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "message": "Listening history saved",
        "history_id": history.id
    }


@app.get("/history/{user_id}")
def get_history(
    user_id: int,
    db: Session = Depends(get_db)
):
    history = db.query(ListeningHistory).filter(
        ListeningHistory.user_id == user_id
    ).order_by(
        ListeningHistory.played_at.desc()
    ).limit(50).all()

    return [
        {
            "song_id": item.song_id,
            "played_at": item.played_at,
            "completion_percentage": item.completion_percentage,
            "completed": item.completed,
            "skipped": item.skipped,
            "liked": item.liked
        }
        for item in history
    ]


@app.post("/like")
def like_song(
    action: TrackAction,
    db: Session = Depends(get_db)
):
    existing = db.query(Like).filter(
        Like.user_id == action.user_id,
        Like.song_id == action.track_id
    ).first()

    if existing:
        return {"message": "Song already liked"}

    new_like = Like(
        user_id=action.user_id,
        song_id=action.track_id
    )

    db.add(new_like)
    db.commit()

    return {"message": "Song liked successfully"}


@app.get("/play-song")
def play_song(
    current_song: str,
    db: Session = Depends(get_db)
):
    song = find_song(db, current_song)

    if not song:
        raise HTTPException(
            status_code=404,
            detail="Song not found in the database"
        )

    try:
        video = find_youtube_video(
            song.track_name,
            song.track_artist or ""
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="YouTube search failed. Check API key and quota."
        ) from exc

    if not video:
        raise HTTPException(
            status_code=404,
            detail="No playable YouTube video found"
        )

    return {
        "song": song_to_dict(song),
        "video": video
    }


@app.get("/recommendations")
def get_recommendations(
    user_id: int,
    current_song: str,
    category: str | None = None,
    mood: str | None = None,
    db: Session = Depends(get_db)
):
    results = recommend(
        db=db,
        user_id=user_id,
        current_song_name=current_song,
        selected_category=category,
        selected_mood=mood,
        number_of_recommendations=1
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No different recommendation found"
        )

    # Always return only one recommendation.
    return results[:1]


@app.get("/next-song")
def get_next_song(
    user_id: int,
    current_song: str,
    exclude_track_id: str | None = None,
    category: str | None = None,
    mood: str | None = None,
    db: Session = Depends(get_db)
):
    results = recommend(
        db=db,
        user_id=user_id,
        current_song_name=current_song,
        selected_category=category,
        selected_mood=mood,
        number_of_recommendations=10
    )

    # Never recommend the currently playing track.
    candidates = [
        item for item in results
        if str(item.get("track_id")) != str(exclude_track_id)
    ]

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="No different next song found"
        )

    # Select one song only.
    song = candidates[0]

    try:
        video = find_youtube_video(
            song.get("track_name", ""),
            song.get("track_artist", "")
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="YouTube search failed. Check API key and quota."
        ) from exc

    if not video:
        raise HTTPException(
            status_code=404,
            detail="No playable video found for the next song"
        )

    return {
        "song": song,
        "video": video
    }
