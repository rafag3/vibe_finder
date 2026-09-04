"""
Carrega data/sample_tracks.csv para data/tracks.db (SQLite).

Rode uma vez antes de subir o Flask:
    python data/load_dataset.py

Troque sample_tracks.csv por um dataset maior (ex: Spotify Tracks Dataset
do Kaggle, remapeando as colunas) sem precisar mudar o resto do projeto -
o app só depende do schema da tabela `tracks`.
"""
import csv
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracks.db"
CSV_PATH = Path(__file__).parent / "sample_tracks.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    genre TEXT,
    valence REAL NOT NULL,       -- 0 (triste/negativo) a 1 (feliz/positivo)
    energy REAL NOT NULL,        -- 0 (calmo) a 1 (intenso)
    tempo REAL,                  -- BPM
    danceability REAL,
    youtube_video_id TEXT,       -- preenchido sob demanda (cache), fica NULL até a 1a busca
    youtube_alt_ids TEXT,        -- JSON list de video_ids alternativos (fallback se o primário bloquear embed)
    artwork_url TEXT,            -- capa via iTunes Search API (grátis, sem cota) - NULL=nunca buscou, ""=buscou e não achou, URL=achou
    preview_url TEXT             -- preview de 30s via iTunes (mesma busca) - fallback de áudio quando o YouTube falha
);

CREATE TABLE IF NOT EXISTS generated_playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mood_text TEXT NOT NULL,
    track_ids TEXT NOT NULL,     -- JSON list de ids
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """ALTER TABLE idempotente: cobre bancos criados antes de uma coluna
    existir, sem precisar apagar dados já cacheados."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(tracks)")}
    if "youtube_alt_ids" not in cols:
        conn.execute("ALTER TABLE tracks ADD COLUMN youtube_alt_ids TEXT")
    if "artwork_url" not in cols:
        conn.execute("ALTER TABLE tracks ADD COLUMN artwork_url TEXT")
    if "preview_url" not in cols:
        conn.execute("ALTER TABLE tracks ADD COLUMN preview_url TEXT")


def load():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    _migrate(conn)

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                r["title"], r["artist"], r["genre"],
                float(r["valence"]), float(r["energy"]),
                float(r["tempo"]), float(r["danceability"]),
            )
            for r in reader
        ]

    conn.execute("DELETE FROM tracks")  # idempotente ao rodar de novo
    conn.executemany(
        """INSERT INTO tracks (title, artist, genre, valence, energy, tempo, danceability)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    print(f"{len(rows)} faixas carregadas em {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    load()
