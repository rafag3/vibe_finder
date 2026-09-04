"""
Pre-popula o cache de video do YouTube e de capa/preview no tracks.db.

Motivo: em hospedagem gratuita o filesystem e EFEMERO - tudo que o app
escrever em runtime some no proximo restart/spin-down. Se o cache nascer
vazio a cada restart, cada clique de play refaz um search.list (100 unidades
de cota, contra 10.000/dia) e a cota do dia evapora.

A solucao e rodar isto LOCALMENTE, com a chave de API na .env, e commitar
o tracks.db ja preenchido. Em producao o app passa a so LER o cache.

Uso:
    cd backend
    python -m data.warm_cache --limit 95          # respeita a cota do dia
    python -m data.warm_cache --limit 95 --skip 95  # no dia seguinte

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

    from cover_art.client import get_metadata
    from youtube.client import get_video_candidates

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, artist FROM tracks "
        "WHERE youtube_video_id IS NULL ORDER BY id LIMIT ? OFFSET ?",
        (args.limit, args.skip),
    ).fetchall()
    conn.close()

    print(f"{len(rows)} faixa(s) sem cache de video nesta janela.")
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

    conn = sqlite3.connect(DB_PATH)
    total, cached = conn.execute(
        "SELECT COUNT(*), COUNT(youtube_video_id) FROM tracks"
    ).fetchone()
    conn.close()
    print(f"\nCache de video: {cached}/{total} faixas. Commite o tracks.db atualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
