"""
Busca capa E preview de 30s via iTunes Search API - pública, sem chave,
sem cota diária (diferente do YouTube). A capa é só visual; o preview_url
vira fallback de ÁUDIO quando o YouTube falha (cota estourada, vídeo
bloqueado) - não substitui a música inteira, mas garante que toca alguma
coisa mesmo sem YouTube disponível.

Cacheados juntos no SQLite (mesma chamada de busca resolve os dois):
NULL = nunca buscou, "" = buscou e não achou nada, valor = achou.
"""
import logging
import sqlite3
from pathlib import Path

import requests

log = logging.getLogger("vibe.cover_art")

DB_PATH = Path(__file__).parent.parent / "data" / "tracks.db"
SEARCH_URL = "https://itunes.apple.com/search"


def get_metadata(track_id: int, title: str, artist: str) -> dict:
    """Retorna {"cover_url": str|None, "preview_url": str|None}."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cached = conn.execute(
        "SELECT artwork_url, preview_url FROM tracks WHERE id = ?", (track_id,)
    ).fetchone()
    if cached and cached["artwork_url"] is not None:
        conn.close()
        return {
            "cover_url": cached["artwork_url"] or None,
            "preview_url": cached["preview_url"] or None,
        }

    result, network_failed = _search(title, artist)
    if network_failed:
        # NÃO cacheia: falha de rede é diferente de "buscou e não achou nada"
        # (ver client.py do youtube pra explicação completa do porquê)
        conn.close()
        return {"cover_url": None, "preview_url": None}

    cover_url = result.get("cover_url") if result else None
    preview_url = result.get("preview_url") if result else None
    conn.execute(
        "UPDATE tracks SET artwork_url = ?, preview_url = ? WHERE id = ?",
        (cover_url or "", preview_url or "", track_id),
    )
    conn.commit()
    conn.close()
    return {"cover_url": cover_url, "preview_url": preview_url}


def _search(title: str, artist: str) -> tuple[dict | None, bool]:
    """Retorna (resultado_ou_none, falhou_por_rede)."""
    params = {
        "term": f"{title} {artist}",
        "media": "music",
        "limit": 1,
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=8)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.warning("busca falhou pra '%s - %s': %s", title, artist, e)
        return None, True

    results = resp.json().get("results", [])
    if not results:
        return None, False

    item = results[0]
    artwork = item.get("artworkUrl100")
    # 100x100 é pequeno demais pra um tile grande no hover - pede 300x300,
    # que é o tamanho real disponível no CDN da Apple pra artes de música
    cover_url = artwork.replace("100x100", "300x300") if artwork else None
    preview_url = item.get("previewUrl")  # mp3 de ~30s, direto, sem auth

    return {"cover_url": cover_url, "preview_url": preview_url}, False
