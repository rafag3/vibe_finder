"""
Cliente minimo pro Supabase (Postgres gerenciado) via REST (PostgREST).

Guarda o que precisa sobreviver a restart/redeploy: cache de video do
YouTube, cache de capa/preview do iTunes e o historico de playlists geradas.
O SQLite local (tracks.db) continua sendo so o catalogo de faixas - estatico,
comitado no git, nunca escrito em runtime.

Por que nao um SDK dedicado: sao poucas chamadas (select/upsert/insert/count)
contra 3 tabelas. requests ja e dependencia do projeto (youtube/client.py,
cover_art/client.py) - mais uma lib so pra isso nao se paga.

Sem SUPABASE_URL/SUPABASE_KEY configuradas, todas as funcoes viram no-op
(retornam None/False) - mesmo padrao de fallback do YOUTUBE_API_KEY: o app
continua funcionando, so sem persistir cache entre restarts.
"""
import logging
import os

import requests

log = logging.getLogger("vibe.supabase")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def select_one(table: str, match: dict) -> dict | None:
    if not enabled():
        return None
    params = {k: f"eq.{v}" for k, v in match.items()}
    params["select"] = "*"
    params["limit"] = "1"
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_HEADERS, params=params, timeout=8)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.warning("select em %s falhou: %s", table, e)
        return None
    rows = resp.json()
    return rows[0] if rows else None


def upsert(table: str, row: dict, on_conflict: str) -> bool:
    """Insere ou atualiza por conflito de chave (ex: track_id ja cacheado)."""
    if not enabled():
        return False
    headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates"}
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            params={"on_conflict": on_conflict},
            json=row,
            timeout=8,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.warning("upsert em %s falhou: %s", table, e)
        return False
    return True


def insert(table: str, row: dict) -> bool:
    if not enabled():
        return False
    try:
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=_HEADERS, json=row, timeout=8)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.warning("insert em %s falhou: %s", table, e)
        return False
    return True


def count(table: str) -> int | None:
    """None = Supabase desabilitado ou request falhou (distinto de 0 = tabela vazia)."""
    if not enabled():
        return None
    headers = {**_HEADERS, "Prefer": "count=exact"}
    try:
        resp = requests.head(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, params={"select": "*"}, timeout=8)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.warning("count em %s falhou: %s", table, e)
        return None
    total = resp.headers.get("content-range", "").split("/")[-1]
    return int(total) if total.isdigit() else None
