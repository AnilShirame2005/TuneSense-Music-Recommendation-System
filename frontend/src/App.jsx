
import {
  useState,
  useRef,
  useEffect,
  useCallback
} from "react";

import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [userId, setUserId] = useState("1");
  const [currentSong, setCurrentSong] = useState("");
  const [category, setCategory] = useState("");
  const [mood, setMood] = useState("");
  const [currentTrack, setCurrentTrack] = useState(null);
  const [nextRecommendation, setNextRecommendation] = useState(null);
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [playerReady, setPlayerReady] = useState(false);

  const playerRef = useRef(null);
  const currentTrackRef = useRef(null);
  const videoRef = useRef(null);
  const loadingRef = useRef(false);
  const startedRef = useRef(false);
  const nextSongRef = useRef(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    currentTrackRef.current = currentTrack;
  }, [currentTrack]);

  useEffect(() => {
    videoRef.current = video;
  }, [video]);

  const saveHistory = useCallback(async (song) => {
    if (!song) return;

    try {
      const response = await fetch(`${API_URL}/history`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: Number(userId),
          track_id: String(song.track_id)
        })
      });

      if (!response.ok) {
        console.warn("History could not be saved.");
      }
    } catch (err) {
      console.error("History error:", err);
    }
  }, [userId]);

  const fetchNextSong = useCallback(async (songName, excludeId = null) => {
    if (!songName?.trim() || loadingRef.current) return;

    loadingRef.current = true;
    setLoading(true);
    setError("");

    const requestId = ++requestIdRef.current;

    try {
      const params = new URLSearchParams({
        user_id: String(userId),
        current_song: songName.trim()
      });

      if (excludeId != null) {
        params.set("exclude_track_id", String(excludeId));
      }

      if (category) params.set("category", category);
      if (mood) params.set("mood", mood);

      const response = await fetch(
        `${API_URL}/next-song?${params.toString()}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Next song could not be found.");
      }

      if (requestId !== requestIdRef.current) return;

      if (
        !data.song ||
        !data.video?.video_id ||
        String(data.song.track_id) === String(excludeId)
      ) {
        throw new Error("The API did not return a different playable song.");
      }

      setCurrentTrack(data.song);
      currentTrackRef.current = data.song;

      setCurrentSong(data.song.track_name || songName);
      setNextRecommendation(null);

      setVideo(data.video);
      videoRef.current = data.video;

      await saveHistory(data.song);
    } catch (err) {
      if (requestId === requestIdRef.current) {
        setError(err.message || "Could not load the next song.");
      }
    } finally {
      if (requestId === requestIdRef.current) {
        loadingRef.current = false;
        setLoading(false);
      }
    }
  }, [userId, category, mood, saveHistory]);

  // Start by playing the song entered by the user.
  const startPlayback = async () => {
    if (!currentSong.trim() || loadingRef.current) {
      if (!currentSong.trim()) {
        setError("Please enter a song name.");
      }
      return;
    }

    loadingRef.current = true;
    setLoading(true);
    setError("");
    setNextRecommendation(null);
    setVideo(null);
    setCurrentTrack(null);
    startedRef.current = false;

    try {
      const params = new URLSearchParams({
        current_song: currentSong.trim()
      });

      const response = await fetch(
        `${API_URL}/play-song?${params.toString()}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not play this song.");
      }

      setCurrentTrack(data.song);
      currentTrackRef.current = data.song;

      setVideo(data.video);
      videoRef.current = data.video;

      startedRef.current = true;

      await saveHistory(data.song);

      // Fetch exactly one recommendation for display.
      try {
        const recParams = new URLSearchParams({
          user_id: String(userId),
          current_song: data.song.track_name
        });

        if (category) recParams.set("category", category);
        if (mood) recParams.set("mood", mood);

        const recResponse = await fetch(
          `${API_URL}/recommendations?${recParams.toString()}`
        );

        const recData = await recResponse.json();

        if (recResponse.ok && Array.isArray(recData) && recData.length) {
          setNextRecommendation(recData[0]);
        }
      } catch (recError) {
        console.warn("Could not load next recommendation:", recError);
      }
    } catch (err) {
      setError(err.message || "Could not start playback.");
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  };

  const playNextAutomatically = useCallback(async () => {
    if (loadingRef.current || !startedRef.current) return;

    const playing = currentTrackRef.current;
    if (!playing) return;

    await fetchNextSong(
      playing.track_name,
      playing.track_id
    );
  }, [fetchNextSong]);

  useEffect(() => {
    nextSongRef.current = playNextAutomatically;
  }, [playNextAutomatically]);

  // Initialize the YouTube IFrame API once per video ID.
  useEffect(() => {
    if (!video?.video_id) return;

    let cancelled = false;
    let instance = null;

    setPlayerReady(false);

    const createPlayer = () => {
      if (cancelled || !window.YT?.Player) return;

      const target = document.getElementById("tunesense-player");
      if (!target) return;

      if (playerRef.current) {
        try {
          playerRef.current.destroy();
        } catch {
          // Ignore cleanup errors.
        }
        playerRef.current = null;
      }

      instance = new window.YT.Player(target, {
        width: "100%",
        height: "315",
        videoId: video.video_id,
        playerVars: {
          playsinline: 1,
          autoplay: 1,
          origin: window.location.origin
        },
        events: {
          onReady: (event) => {
            if (cancelled) return;

            playerRef.current = event.target;
            setPlayerReady(true);
            event.target.playVideo();
          },

          onStateChange: (event) => {
            if (
              event.data === window.YT.PlayerState.ENDED &&
              startedRef.current
            ) {
              void nextSongRef.current?.();
            }
          },

          onError: (event) => {
            console.error("YouTube player error:", event.data);
            setError(
              "This YouTube video could not be played. Try another song."
            );
          }
        }
      });

      playerRef.current = instance;
    };

    const loadYouTubeAPI = () => {
      if (window.YT?.Player) {
        createPlayer();
        return;
      }

      const existing = document.querySelector(
        'script[data-tunesense-youtube="true"]'
      );

      if (!existing) {
        const script = document.createElement("script");
        script.src = "https://www.youtube.com/iframe_api";
        script.dataset.tunesenseYoutube = "true";
        document.head.appendChild(script);
      }

      const oldCallback = window.onYouTubeIframeAPIReady;

      window.onYouTubeIframeAPIReady = () => {
        if (typeof oldCallback === "function") oldCallback();
        createPlayer();
      };
    };

    loadYouTubeAPI();

    return () => {
      cancelled = true;

      if (playerRef.current) {
        try {
          playerRef.current.destroy();
        } catch {
          // Ignore cleanup errors.
        }
        playerRef.current = null;
      }
    };
  }, [video?.video_id]);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>🎵 TuneSense</h1>
          <p>AI Music Recommendation System</p>
        </div>

        <div className="user-box">
          <label htmlFor="userId">User ID</label>
          <input
            id="userId"
            type="number"
            min="1"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
        </div>
      </header>

      <main>
        <section className="search-card">
          <h2>Play Your Song 🎧</h2>

          <div className="form-group">
            <label htmlFor="currentSong">Song Name</label>
            <input
              id="currentSong"
              type="text"
              placeholder="e.g. Dil To Hai Dil"
              value={currentSong}
              onChange={(e) => setCurrentSong(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !loading) {
                  void startPlayback();
                }
              }}
            />
          </div>

          <div className="filters">
            <div className="form-group">
              <label htmlFor="category">Category</label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">Any Category</option>
                <option value="pop">Pop</option>
                <option value="hip hop">Hip Hop</option>
                <option value="rock">Rock</option>
                <option value="edm">EDM</option>
                <option value="classical">Classical</option>
                <option value="jazz">Jazz</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="mood">Mood</label>
              <select
                id="mood"
                value={mood}
                onChange={(e) => setMood(e.target.value)}
              >
                <option value="">Any Mood</option>
                <option value="happy">Happy</option>
                <option value="sad">Sad</option>
                <option value="energetic">Energetic</option>
                <option value="relaxed">Relaxed</option>
                <option value="romantic">Romantic</option>
                <option value="intense">Intense</option>
              </select>
            </div>
          </div>

          <button
            className="recommend-button"
            onClick={() => void startPlayback()}
            disabled={loading}
          >
            {loading ? "Loading song..." : "▶ Play Song"}
          </button>

          {error && <p className="error">{error}</p>}
        </section>

        {currentTrack && video && (
          <section className="search-card">
            <h2>▶ Now Playing</h2>
            <h3>{currentTrack.track_name}</h3>
            <p>{currentTrack.track_artist || "Unknown Artist"}</p>

            <div id="tunesense-player" />

            {!playerReady && <p>Loading player...</p>}
          </section>
        )}

        {nextRecommendation && (
          <section className="search-card">
            <h2>Next Recommended Song</h2>
            <h3>{nextRecommendation.track_name}</h3>
            <p>{nextRecommendation.track_artist || "Unknown Artist"}</p>
          </section>
        )}
      </main>

      <footer>🎵 TuneSense AI Music Recommendation System</footer>
    </div>
  );
}

export default App;
