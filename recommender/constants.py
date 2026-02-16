"""Weight constants that tune recommendation behavior."""

REQUESTED_GENRE_WEIGHT = 0.4 # Requested Genres
REQUESTED_THEME_WEIGHT = 0.2 # Requested Themes
HISTORY_GENRE_WEIGHT = 0.075 # Previously Requested Genres
HISTORY_THEME_WEIGHT = 0.04 # Previously Requested Themes
READ_TITLES_GENRE_WEIGHT = 0.2 # Previously Ranked Read Mangas Genres
READ_TITLES_THEME_WEIGHT = 0.1 # Previously Ranked Read Mangas Themes

MATCH_VS_INTERNAL_WEIGHT = 0.7 # Ratio of score between Match score and Internal Score (70% Match, 30% Internal)

# Optional novelty boost for "less popular" toggle
NOVELTY_WEIGHT = 0.12

# Phase 2 personalization (signal affinities)
SIGNAL_GENRE_WEIGHT = 0.1
SIGNAL_THEME_WEIGHT = 0.05
PERSONALIZATION_MIN_RATINGS = 10
PERSONALIZATION_FULL_RATINGS = 30
