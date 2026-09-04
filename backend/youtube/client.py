"""
Busca o video_id do YouTube para uma faixa e CACHEIA no Supabase.

Isso nao e opcional: search.list custa 100 unidades de cota contra um
limite diario de 10.000 no tier gratuito - sem cache, ~100 buscas sem
repetir faixa ja estoura a cota do dia inteiro.

O cache mora no Supabase (nao no SQLite local) porque o filesystem do
Render free e efemero - qualquer coisa escrita em runtime some no proximo
restart/redeploy. Sem cache persistente, cada deploy zera o progresso e
volta a queimar cota do zero.

Sem YOUTUBE_API_KEY configurada, cai em modo mock (video_id fixo de
placeholder) para o resto do sistema continuar funcionavel em dev/demo.
"""
import logging
import os

import requests

from storage.supabase_client import select_one, upsert

log = logging.getLogger("vibe.youtube")

API_KEY = os.environ.get("YOUTUBE_API_KEY")
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def _error_reason(resp) -> str:
    """Extrai o 'reason' do envelope de erro do Google (quotaExceeded,
    keyInvalid, accessNotConfigured...). Retorna '?' se o corpo não for
    o JSON esperado - nunca levanta exceção dentro de um log."""
    try:
        errors = resp.json().get("error", {}).get("errors", [])
        return errors[0].get("reason", "?") if errors else "?"
    except Exception:  # noqa: BLE001 - caminho de diagnóstico, não pode quebrar
        return "?"

# video_id de placeholder usado quando não há API key - troque por algo
# real ou deixe assim para testar o fluxo completo sem gastar cota
MOCK_VIDEO_ID = "dQw4w9WgXcQ"


def get_video_candidates(track_id: int, title: str, artist: str) -> list[str]:
    """Retorna a lista de video_ids candidatos pra faixa (primário + fallbacks).
    Cacheados no Supabase (tabela video_cache) - uma linha de busca cobre
    N tentativas de reprodução, sem gastar cota de novo a cada bloqueio."""
    cached = select_one("video_cache", {"track_id": track_id})
    if cached and cached.get("youtube_video_id"):
        return [cached["youtube_video_id"], *(cached.get("youtube_alt_ids") or [])]

    if not API_KEY:
        # modo mock: NÃO grava no cache, senão quando a chave for
        # configurada depois o app acha que já resolveu e nunca busca
        return [MOCK_VIDEO_ID]

    candidates = _search(title, artist)
    if not candidates:
        # busca falhou (chave inválida, cota estourada, rede fora) ou não
        # achou nada - cai pro mock em vez de derrubar a resposta inteira.
        # NÃO cacheia esse resultado: se a causa for temporária (chave
        # corrigida depois, cota resetou à meia-noite), a próxima geração
        # tenta de novo em vez de ficar presa no mock pra sempre.
        return [MOCK_VIDEO_ID]
    primary, alt_ids = candidates[0], candidates[1:]
    upsert(
        "video_cache",
        {"track_id": track_id, "youtube_video_id": primary, "youtube_alt_ids": alt_ids},
        on_conflict="track_id",
    )
    return candidates


def _search(title: str, artist: str, max_results: int = 5) -> list[str]:
    """Retorna até max_results video_ids candidatos, na ordem de relevância.
    Pedir vários em vez de um só é o que permite o front-end tentar um
    upload alternativo quando o primeiro tem embedding externo bloqueado
    pelo dono do canal (erro 101/150 - não tem como saber isso de antemão,
    só na hora de tocar).

    Nunca deixa exceção subir: chave inválida, cota estourada ou rede fora
    não podem derrubar o /generate inteiro por causa de UMA faixa - melhor
    essa faixa cair pro mock e o resto da playlist continuar funcionando."""
    params = {
        "part": "snippet",
        "q": f"{title} {artist} official audio",
        "type": "video",
        "maxResults": max_results,
        "videoEmbeddable": "true",  # filtro geral, não garante o caso por-vídeo
        "key": API_KEY,
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        log.warning("busca falhou pra '%s - %s': %s", title, artist, e)
        return []

    if resp.status_code != 200:
        # O corpo é a única coisa que distingue as causas entre si:
        # quotaExceeded, keyInvalid e accessNotConfigured chegam todas
        # como 403 e exigem correções completamente diferentes.
        log.warning(
            "HTTP %s pra '%s - %s' [%s]: %s",
            resp.status_code, title, artist,
            _error_reason(resp), resp.text[:300],
        )
        return []
    items = resp.json().get("items", [])
    return [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]
