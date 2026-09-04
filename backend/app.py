import os
import sqlite3
from pathlib import Path


def _load_dotenv() -> None:
    """Carrega data/../.env para os.environ (sem depender de python-dotenv).
    Roda ANTES de importar youtube.client, que lê YOUTUBE_API_KEY no import."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    text = env_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

import logging  # noqa: E402

from flask import Flask, jsonify, request  # noqa: E402
from flask_cors import CORS  # noqa: E402
from flask_limiter import Limiter  # noqa: E402
from flask_limiter.util import get_remote_address  # noqa: E402
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402

from matching.engine import find_tracks_by_genre  # noqa: E402
from youtube.client import API_KEY, get_video_candidates  # noqa: E402
from cover_art.client import get_metadata  # noqa: E402
from storage.supabase_client import count as supabase_count, enabled as supabase_enabled, insert as supabase_insert  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("vibe.app")

DB_PATH = Path(__file__).parent / "data" / "tracks.db"

app = Flask(__name__)
# API pura consumida por um front separado (Vite dev server em outra porta) -
# CORS liberado só pras origens de dev/produção do front, não "*".
CORS(app, resources={r"/*": {"origins": os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173").split(",")}})

# Atrás do proxy do Render, request.remote_addr é o IP do proxy, não o do
# cliente. Sem isso o rate limit trataria TODO MUNDO como um único IP e
# limitaria os usuários uns aos outros. x_for=1 = confia em um salto.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Storage em memória: correto com 1 worker (nossa config no Render). Se um
# dia rodar com múltiplos workers/instâncias, cada processo teria seu próprio
# contador e o limite efetivo seria N vezes maior - aí precisa de Redis.
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
    strategy="fixed-window",
)


@app.route("/health")
def health():
    """Diagnóstico, não só liveness. Reporta o que realmente costuma
    quebrar em produção: chave ausente e Supabase não configurado (cache
    cairia pra vazio a cada restart, já que o filesystem local é efêmero)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        conn.close()
    except sqlite3.Error as e:
        log.error("health check falhou ao ler o banco: %s", e)
        return jsonify({"status": "degraded", "error": "banco inacessível"}), 503

    cached = supabase_count("video_cache")
    return jsonify({
        "status": "ok",
        "tracks": total,
        "video_cache": f"{cached}/{total}" if cached is not None else "indisponível",
        "youtube_key": bool(API_KEY),  # booleano, nunca a chave em si
        "supabase": supabase_enabled(),
    })


@app.route("/generate", methods=["POST"])
@limiter.limit("10 per minute; 60 per hour")
def generate():
    payload = request.get_json(silent=True) or {}
    mood_text = (payload.get("mood") or "").strip()

    if not mood_text:
        return jsonify({"error": "Descreva o mood em algumas palavras."}), 400
    if len(mood_text) > 300:
        return jsonify({"error": "Texto muito longo (máx. 300 caracteres)."}), 400

    # 8 gêneros x 6 faixas = até 48 faixas (era 4x3=12). Sem risco de cota
    # agora: /generate não busca vídeo nenhum (isso só acontece no clique,
    # ver /tracks/<id>/video), então mostrar mais quadrados na grade não
    # custa YouTube nenhum - só mais chamadas ao iTunes pra capa, que não
    # tem limite diário.
    tracks = find_tracks_by_genre(mood_text, genres_limit=8, per_genre=6)
    for t in tracks:
        meta = get_metadata(t["id"], t["title"], t["artist"])
        t["cover_url"] = meta["cover_url"]
        t["preview_url"] = meta["preview_url"]

    _save_history(mood_text, [t["id"] for t in tracks])

    return jsonify({"mood": mood_text, "tracks": tracks})


@app.route("/tracks/<int:track_id>/video")
# O endpoint mais caro do sistema: cada miss de cache custa 100 unidades das
# 10.000 diárias. Um `for id in 1..127` sem limite queima a cota inteira em
# segundos. 30/min é folgado pra quem ouve de verdade e mata o script.
@limiter.limit("30 per minute; 300 per hour")
def track_video(track_id):
    """Busca (ou lê do cache) o vídeo de UMA faixa - só é chamada quando o
    usuário efetivamente clica pra tocar, não em toda a playlist gerada."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT title, artist FROM tracks WHERE id = ?", (track_id,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Faixa não encontrada."}), 404

    candidates = get_video_candidates(track_id, row["title"], row["artist"])
    return jsonify({"youtube_video_id": candidates[0], "youtube_alt_ids": candidates[1:]})


def _save_history(mood_text: str, track_ids: list[int]) -> None:
    supabase_insert("generated_playlists", {"mood_text": mood_text, "track_ids": track_ids})


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
