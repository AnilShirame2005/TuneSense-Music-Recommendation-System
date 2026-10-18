
import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import Song, ListeningHistory

FEATURES = [
    "danceability",
    "energy",
    "acousticness",
    "instrumentalness",
    "valence",
    "tempo",
]


def recommend(
    db: Session,
    user_id: int,
    current_song_name: str,
    selected_category=None,
    selected_mood=None,
    number_of_recommendations=5,
    exclude_track_ids=None,
):
    excluded_ids = {
        str(track_id)
        for track_id in (exclude_track_ids or [])
        if track_id is not None and str(track_id).strip()
    }

    current_song = db.query(Song).filter(
        func.lower(func.trim(Song.track_name))
        == current_song_name.strip().lower()
    ).first()

    if current_song is None:
        print("Song not found:", current_song_name)
        return []

    # Always exclude the current song too.
    excluded_ids.add(str(current_song.track_id))

    songs = db.query(Song).all()
    if not songs:
        return []

    data = pd.DataFrame([
        {
            "track_id": s.track_id,
            "track_name": s.track_name,
            "track_artist": s.track_artist,
            "genre": s.genre,
            "subgenre": s.subgenre,
            "mood": s.mood,
            "danceability": s.danceability,
            "energy": s.energy,
            "acousticness": s.acousticness,
            "instrumentalness": s.instrumentalness,
            "valence": s.valence,
            "tempo": s.tempo,
            "popularity": s.popularity,
        }
        for s in songs
    ])

    if data.empty:
        return []

    for feature in FEATURES:
        data[feature] = pd.to_numeric(
            data[feature], errors="coerce"
        ).fillna(0)

    data["popularity"] = pd.to_numeric(
        data["popularity"], errors="coerce"
    ).fillna(0)

    scaler = StandardScaler()
    matrix = scaler.fit_transform(data[FEATURES])

    current_rows = data.index[
        data["track_id"].astype(str)
        == str(current_song.track_id)
    ]

    if len(current_rows) == 0:
        return []

    current_index = current_rows[0]

    data["similarity"] = cosine_similarity(
        matrix[current_index].reshape(1, -1),
        matrix,
    )[0]

    # Exclude every track already played in this queue.
    data = data[
        ~data["track_id"].astype(str).isin(excluded_ids)
    ].copy()

    if data.empty:
        return []

    history = db.query(ListeningHistory).filter(
        ListeningHistory.user_id == user_id
    ).all()

    listened_ids = {str(h.song_id) for h in history}

    data["history_score"] = data["track_id"].apply(
        lambda track_id: -0.20
        if str(track_id) in listened_ids else 0.05
    )

    preferred_genres = set()

    for item in history:
        old_song = db.query(Song).filter(
            Song.track_id == item.song_id
        ).first()

        if old_song and old_song.genre:
            preferred_genres.add(old_song.genre.lower())

    data["genre_score"] = data["genre"].apply(
        lambda value: 0.20
        if isinstance(value, str)
        and value.lower() in preferred_genres
        else 0.0
    )

    if selected_category:
        category = selected_category.lower()

        matches = (
            data["genre"].fillna("").str.lower().str.contains(category)
            | data["subgenre"].fillna("").str.lower().str.contains(category)
        )

        data["category_score"] = np.where(matches, 0.30, -0.10)
    else:
        data["category_score"] = 0.0

    if selected_mood:
        mood = selected_mood.lower()
        matches = data["mood"].fillna("").str.lower().str.contains(mood)
        data["mood_score"] = np.where(matches, 0.30, -0.05)
    else:
        data["mood_score"] = 0.0

    max_popularity = max(float(data["popularity"].max()), 1.0)
    data["popularity_score"] = (
        data["popularity"] / max_popularity
    ) * 0.10

    data["final_score"] = (
        data["similarity"] * 0.55
        + data["genre_score"] * 0.15
        + data["mood_score"] * 0.10
        + data["category_score"] * 0.10
        + data["history_score"] * 0.05
        + data["popularity_score"] * 0.05
    )

    result = data.sort_values(
        "final_score", ascending=False
    ).head(number_of_recommendations)[
        [
            "track_id",
            "track_name",
            "track_artist",
            "genre",
            "subgenre",
            "mood",
            "similarity",
            "final_score",
        ]
    ].copy()

    result = result.astype(object).where(pd.notna(result), None)
    return result.to_dict(orient="records")
