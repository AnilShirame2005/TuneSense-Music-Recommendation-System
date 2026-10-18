import pandas as pd

from database import SessionLocal, Song


# ============================================================
# LOAD CSV
# ============================================================

CSV_FILE = "data/cleaned_songs.csv"

df = pd.read_csv(CSV_FILE)

print("CSV loaded!")
print("Songs found:", len(df))


# ============================================================
# CREATE MOOD
# ============================================================

def get_mood(row):

    energy = row["energy"]
    valence = row["valence"]

    if energy >= 0.70 and valence >= 0.60:
        return "Energetic"

    elif energy >= 0.70 and valence < 0.60:
        return "Intense"

    elif energy < 0.50 and valence >= 0.60:
        return "Happy"

    elif energy < 0.50 and valence < 0.40:
        return "Sad"

    elif energy < 0.50:
        return "Relaxing"

    else:
        return "Balanced"


df["mood"] = df.apply(get_mood, axis=1)


# ============================================================
# CONNECT TO MYSQL
# ============================================================

db = SessionLocal()

print("Connected to MySQL!")


# ============================================================
# IMPORT SONGS
# ============================================================

songs = []

for _, row in df.iterrows():

    song = Song(

        track_id=str(row["track_id"]),

        track_name=str(row["track_name"]),

        track_artist=str(row["track_artist"]),

        genre=str(row["playlist_genre"]),

        subgenre=str(row["playlist_subgenre"]),

        mood=str(row["mood"]),

        danceability=float(row["danceability"]),

        energy=float(row["energy"]),

        acousticness=float(row["acousticness"]),

        instrumentalness=float(row["instrumentalness"]),

        valence=float(row["valence"]),

        tempo=float(row["tempo"]),

        popularity=int(row["track_popularity"])
    )

    songs.append(song)


# ============================================================
# INSERT IN BATCHES
# ============================================================

BATCH_SIZE = 1000

total = len(songs)

for start in range(0, total, BATCH_SIZE):

    batch = songs[start:start + BATCH_SIZE]

    db.add_all(batch)

    db.commit()

    print(
        f"Imported {min(start + BATCH_SIZE, total)} "
        f"/ {total} songs"
    )


# ============================================================
# CLOSE DATABASE
# ============================================================

db.close()

print()
print("=" * 60)
print("ALL SONGS IMPORTED SUCCESSFULLY!")
print("=" * 60)