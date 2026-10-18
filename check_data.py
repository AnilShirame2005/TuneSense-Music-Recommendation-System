import pandas as pd

# Load dataset
df = pd.read_csv("data/spotify_songs (2).csv")

print("Original shape:", df.shape)

# Check missing values
print("\nMissing values:")
print(df.isnull().sum())

# Remove rows where important information is missing
df = df.dropna(subset=[
    "track_name",
    "track_artist",
    "playlist_genre",
    "danceability",
    "energy",
    "acousticness",
    "instrumentalness",
    "valence",
    "tempo"
])

# Remove duplicate songs
df = df.drop_duplicates(subset="track_id")

print("\nShape after cleaning:", df.shape)

# Check again for missing values
print("\nMissing values after cleaning:")
print(df.isnull().sum())

df.to_csv("data/cleaned_songs.csv", index=False)

print("\nCleaned dataset saved successfully!")