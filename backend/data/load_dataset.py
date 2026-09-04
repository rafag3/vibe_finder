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
    danceability REAL
);
"""
# Cache de video (YouTube), capa/preview (iTunes) e historico de playlists
# geradas moram no Supabase (ver storage/supabase_client.py), nao aqui - este
# banco e so o catalogo estatico de faixas, comitado no git, nunca escrito
# em runtime. Ver DEPLOY.md pro motivo (filesystem efemero em produção).


def load():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

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
