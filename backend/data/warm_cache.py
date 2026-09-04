"""
Pre-popula o cache de video do YouTube e de capa/preview no Supabase
(video_cache / cover_cache) - o cache persiste la, nao no SQLite local, entao
sobrevive a restart/redeploy do Render mesmo sem commitar nada.

Ainda vale rodar isto antes de mostrar o app pra alguem: cada faixa sem
cache custa ~100 unidades de cota (search.list) contra um limite de
10.000/dia, entao popular o cache com antecedencia evita que os primeiros
~100 plays reais do dia queimem a cota inteira.

Uso:
    cd backend
    python -m data.warm_cache --limit 95            # respeita a cota do dia
    python -m data.warm_cache --limit 95 --skip 95   # no dia seguinte (o que ja
                                                      # estiver cacheado e pulado
                                                      # de graca, sem gastar cota)

Cota: cada faixa sem cache custa ~100 unidades (search.list). Com 10.000/dia
cabem ~100 faixas por dia. As capas (iTunes) nao tem cota.
"""
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
DB_PATH = BASE_DIR / "data" / "tracks.db"


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=95, help="quantas faixas processar")
    parser.add_argument("--skip", type=int, default=0, help="quantas faixas pular")
    parser.add_argument("--covers-only", action="store_true", help="so capas, sem gastar cota do YouTube")
    args = parser.parse_args()

    _load_dotenv()
    if not args.covers_only and not os.environ.get("YOUTUBE_API_KEY"):
        print("ERRO: YOUTUBE_API_KEY nao configurada - sem ela o client cai em modo mock.")
        return 1
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
        print("ERRO: SUPABASE_URL/SUPABASE_KEY nao configuradas - sem elas nada e cacheado.")
        return 1

    from cover_art.client import get_metadata
    from storage.supabase_client import count as supabase_count
    from youtube.client import get_video_candidates

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, artist FROM tracks ORDER BY id LIMIT ? OFFSET ?",
        (args.limit, args.skip),
    ).fetchall()
    conn.close()

    print(f"Processando {len(rows)} faixa(s) - as ja cacheadas no Supabase sao puladas de graca.")
    for i, row in enumerate(rows, 1):
        label = f"{row['artist']} - {row['title']}"
        try:
            get_metadata(row["id"], row["title"], row["artist"])
            if not args.covers_only:
                ids = get_video_candidates(row["id"], row["title"], row["artist"])
                print(f"[{i}/{len(rows)}] {label} -> {ids[0]} (+{len(ids) - 1} alt)")
            else:
                print(f"[{i}/{len(rows)}] {label} -> capa ok")
        except Exception as exc:  # noqa: BLE001 - script de manutencao, segue adiante
            print(f"[{i}/{len(rows)}] {label} -> FALHOU: {exc}")
        time.sleep(0.2)  # educado com as duas APIs

    total_cached = supabase_count("video_cache")
    print(f"\nCache de video no Supabase: {total_cached} faixa(s) no total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
