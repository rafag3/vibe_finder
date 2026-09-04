"""
Busca capa E preview de 30s via iTunes Search API - pública, sem chave,
sem cota diária (diferente do YouTube). A capa é só visual; o preview_url
vira fallback de ÁUDIO quando o YouTube falha (cota estourada, vídeo
bloqueado) - não substitui a música inteira, mas garante que toca alguma
coisa mesmo sem YouTube disponível.

Cacheados no Supabase (tabela cover_cache), mesmo motivo do video_cache em
youtube/client.py: filesystem do Render free é efêmero, cache local some a
cada restart/redeploy.
"""
import logging

import requests

from storage.supabase_client import select_one, upsert

log = logging.getLogger("vibe.cover_art")

SEARCH_URL = "https://itunes.apple.com/search"


def get_metadata(track_id: int, title: str, artist: str) -> dict:
    """Retorna {"cover_url": str|None, "preview_url": str|None}."""
    cached = select_one("cover_cache", {"track_id": track_id})
    if cached is not None:
        return {
            "cover_url": cached.get("artwork_url") or None,
            "preview_url": cached.get("preview_url") or None,
        }

    result, network_failed = _search(title, artist)
    if network_failed:
        # NÃO cacheia: falha de rede é diferente de "buscou e não achou nada"
        # (ver client.py do youtube pra explicação completa do porquê)
        return {"cover_url": None, "preview_url": None}

    cover_url = result.get("cover_url") if result else None
    preview_url = result.get("preview_url") if result else None
    upsert(
        "cover_cache",
        {"track_id": track_id, "artwork_url": cover_url or "", "preview_url": preview_url or ""},
        on_conflict="track_id",
    )
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
