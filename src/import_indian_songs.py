import pandas as pd
from database import get_db, Song


# -----------------------------
# File locations
# -----------------------------
HINDI_FILE = "../data/Hindi_songs.csv"
MARATHI_FILE = "../data/Marathi_songs.csv"


# -----------------------------
# Read datasets
# -----------------------------
hindi = pd.read_csv(HINDI_FILE)
marathi = pd.read_csv(MARATHI_FILE)

# Make column names consistent
hindi.columns = hindi.columns.str.strip().str.lower()
marathi.columns = marathi.columns.str.strip().str.lower()


# -----------------------------
# Combine both datasets
# -----------------------------
songs_data = pd.concat(
    [hindi, marathi],
    ignore_index=True
)

print("Hindi songs:", len(hindi))
print("Marathi songs:", len(marathi))
print("Total new songs:", len(songs_data))


# -----------------------------
# Get database session
# -----------------------------
db = next(get_db())

added = 0
skipped = 0


# -----------------------------
# Get existing songs ONCE
# -----------------------------
print("\nChecking existing songs...")

existing_songs = db.query(
    Song.track_name,
    Song.track_artist
).all()

existing_pairs = {
    (
        str(song.track_name).strip(),
        str(song.track_artist).strip()
    )
    for song in existing_songs
}

print("Existing songs in database:", len(existing_pairs))


# -----------------------------
# Add songs
# -----------------------------
for index, row in songs_data.iterrows():

    song_name = str(row["song_name"]).strip()
    singer = str(row["singer"]).strip()
    language = str(row["language"]).strip()

    pair = (song_name, singer)

    # Skip duplicate song + artist
    if pair in existing_pairs:
        skipped += 1
        continue

    # -------------------------
    # Create unique track ID
    # -------------------------
    track_id = f"IND_{index + 1}"

    new_song = Song(
        track_id=track_id,

        track_name=song_name,
        track_artist=singer,

        # Language stored in genre
        genre=language,

        # Not available
        subgenre=None,
        mood=None,

        # Audio features
        danceability=float(row["danceability"])
            if pd.notna(row["danceability"]) else 0.0,

        energy=float(row["energy"])
            if pd.notna(row["energy"]) else 0.0,

        acousticness=float(row["acousticness"])
            if pd.notna(row["acousticness"]) else 0.0,

        instrumentalness=0.0,

        valence=float(row["valence"])
            if pd.notna(row["valence"]) else 0.0,

        tempo=float(row["tempo"])
            if pd.notna(row["tempo"]) else 0.0,

        popularity=0
    )

    db.add(new_song)

    # Add to our set so duplicates inside
    # the new datasets are also skipped
    existing_pairs.add(pair)

    added += 1


    # -------------------------
    # COMMIT EVERY 100 SONGS
    # -------------------------
    if added % 100 == 0:
        db.commit()
        print(f"Saved {added} new songs...")


# -----------------------------
# Final commit
# -----------------------------
db.commit()


# -----------------------------
# Result
# -----------------------------
print("\n================================")
print("IMPORT COMPLETED")
print("================================")
print("Songs added:", added)
print("Songs skipped:", skipped)
print("Total processed:", len(songs_data))