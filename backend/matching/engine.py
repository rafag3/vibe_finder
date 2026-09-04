"""
Motor de matching: texto livre de mood -> (valence, energy) alvo -> ranking
das faixas do dataset por distância euclidiana nesses dois eixos.

Abordagem intencionalmente simples (keyword -> vetor), não embeddings:
é fácil de explicar e defender numa banca, sem dependência de modelo externo,
e o resultado é totalmente determinístico (mesma entrada = mesma saída,
importante pra depurar e demonstrar).
"""
import math
import sqlite3
import unicodedata
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "tracks.db"

# Cada palavra-chave aponta para uma região do espaço (valence, energy).
# Isso é o "modelo" - trocar/expandir esse dicionário é a forma principal
# de melhorar a qualidade do matching sem tocar no resto do sistema.
#
# As chaves são RADICAIS sem acento (o texto de entrada é normalizado antes
# do match), então "trein" pega treino/treinar/treinando, "calm" pega
# calmo/calma/acalmar, etc. Mantenha as chaves curtas o suficiente pra
# cobrir as flexões, mas não tão curtas que peguem palavras não relacionadas.
KEYWORD_MAP = {
    # tristeza / melancolia -> valence baixo
    "trist": (0.15, 0.30), "melanc": (0.15, 0.25), "saudade": (0.20, 0.25),
    "chor": (0.20, 0.20), "sozinh": (0.20, 0.30), "solidao": (0.18, 0.25),
    "deprim": (0.12, 0.25), "vazio": (0.15, 0.22),

    # animação / festa -> valence e energy altos
    "feliz": (0.85, 0.65), "alegr": (0.85, 0.65), "festa": (0.85, 0.85),
    "anima": (0.80, 0.80), "comemora": (0.85, 0.75), "empolga": (0.80, 0.78),
    "danc": (0.80, 0.80), "balada": (0.80, 0.82),
    "euforia": (0.85, 0.88), "vibe boa": (0.82, 0.70),

    # energia física / treino -> energy alto, valence médio-alto
    "trein": (0.65, 0.90), "academia": (0.65, 0.90), "corr": (0.60, 0.88),
    "corrida": (0.60, 0.88), "pedal": (0.60, 0.85), "foco": (0.55, 0.70),
    "trabalh": (0.55, 0.55), "estud": (0.50, 0.35), "produtiv": (0.55, 0.60),

    # calma / relaxamento -> energy baixo
    "relax": (0.55, 0.15), "calm": (0.55, 0.15), "dorm": (0.45, 0.08),
    "medit": (0.50, 0.10), "chuva": (0.40, 0.20), "tranquil": (0.55, 0.18),
    "descans": (0.50, 0.15), "paz": (0.55, 0.15),

    # raiva / intensidade -> energy alto, valence baixo-médio
    "raiva": (0.30, 0.85), "irritad": (0.30, 0.80), "bravo": (0.30, 0.80),
    "intens": (0.40, 0.88), "adrenalina": (0.55, 0.92),
    "ansi": (0.30, 0.60), "estress": (0.25, 0.65), "nervos": (0.30, 0.62),

    # romance / nostalgia -> valence médio-alto, energy baixo-médio
    "romant": (0.70, 0.35), "amor": (0.72, 0.40), "paixao": (0.72, 0.45),
    "nostalg": (0.55, 0.30), "apaixona": (0.75, 0.42),

    # sofrência / término -> valence baixo, energy baixo-médio (mais "movido"
    # que tristeza pura - sertanejo sofrência costuma ter batida, não é balada)
    "sofrenc": (0.18, 0.35), "termin": (0.20, 0.30), "traicao": (0.15, 0.35),
    "corno": (0.15, 0.40), "bebend": (0.25, 0.40),
}

DEFAULT_TARGET = (0.55, 0.50)  # neutro, se nenhuma keyword bater

# Palavras que invertem o sentido da keyword que vem logo depois.
# Sem isso, "não quero nada triste" casa com "trist" e devolve exatamente
# o oposto do que foi pedido - a falha mais visível do matching por substring.
NEGATORS = {
    "nao", "nada", "nem", "nenhum", "nenhuma", "sem", "menos",
    "evitar", "evita", "evite", "exceto", "tirando", "fora",
}

# Quantos tokens antes da keyword são inspecionados em busca de um negador.
# 3 cobre as construções comuns do português falado ("não quero nada triste",
# "sem ser muito animado") sem alcançar orações anteriores, onde um "não"
# solto não tem relação com a keyword ("não aguento mais, tô na tristeza").
NEGATION_WINDOW = 3


def _normalize(text: str) -> str:
    """minúsculas + remove acentos, pra 'ânsia'/'ansia' baterem na mesma chave."""
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _is_negated(text: str, keyword_pos: int) -> bool:
    """Procura um negador nos NEGATION_WINDOW tokens anteriores à keyword.

    A janela é truncada na keyword anterior, se houver: um negador que já se
    aplicou a uma keyword não pode alcançar a seguinte. Sem esse corte, em
    "sem nada triste, quero dançar" o "nada" negaria tanto 'trist' quanto
    'danc' e a frase devolveria o oposto de si mesma.
    """
    preceding = text[:keyword_pos]

    # fim da última keyword que aparece antes desta
    corte = 0
    for kw in KEYWORD_MAP:
        pos = preceding.rfind(kw)
        if pos != -1:
            corte = max(corte, pos + len(kw))

    janela = preceding[corte:].replace(",", " ").replace(";", " ").split()
    return any(tok in NEGATORS for tok in janela[-NEGATION_WINDOW:])


def _extract_target(mood_text: str) -> tuple[float, float]:
    text = _normalize(mood_text)

    matches: list[tuple[float, float]] = []
    for kw, (valence, energy) in KEYWORD_MAP.items():
        pos = text.find(kw)
        if pos == -1:
            continue
        if _is_negated(text, pos):
            # inverte o vetor no espaço: "nada triste" (0.15, 0.30) vira
            # (0.85, 0.70). Não é o mesmo que "alegre", mas aponta pro lado
            # certo do plano, que é o que importa pro ranking por distância.
            matches.append((1.0 - valence, 1.0 - energy))
        else:
            matches.append((valence, energy))

    if not matches:
        return DEFAULT_TARGET
    # média dos vetores encontrados - permite combinar moods ("triste mas
    # quero dançar" pega tanto o vetor de tristeza quanto o de festa)
    valence = sum(v for v, _ in matches) / len(matches)
    energy = sum(e for _, e in matches) / len(matches)
    return valence, energy


def find_tracks(mood_text: str, limit: int = 10) -> list[dict]:
    target_valence, target_energy = _extract_target(mood_text)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM tracks").fetchall()
    conn.close()

    def distance(row):
        return math.dist(
            (row["valence"], row["energy"]),
            (target_valence, target_energy),
        )

    ranked = sorted(rows, key=distance)[:limit]
    return [dict(r) for r in ranked]


def find_tracks_by_genre(
    mood_text: str, genres_limit: int = 6, per_genre: int = 4
) -> list[dict]:
    """Como find_tracks, mas diversificado por gênero em vez de pegar só
    o top-N global. Sem isso, um mood específico (ex: "saudade") tende a
    ter um gênero dominando toda a região do espaço valence/energy e os
    outros gêneros somem do resultado inteiro - o oposto do que faz
    sentido pra uma grade visual separada por estilo musical.

    Estratégia: ranqueia gêneros pela distância do seu melhor candidato
    (quão bem aquele estilo consegue representar o mood pedido), pega os
    `genres_limit` gêneros mais relevantes, e dentro de cada um pega os
    `per_genre` mais próximos.
    """
    target_valence, target_energy = _extract_target(mood_text)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM tracks").fetchall()
    conn.close()

    def distance(row):
        return math.dist(
            (row["valence"], row["energy"]),
            (target_valence, target_energy),
        )

    by_genre: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        by_genre.setdefault(row["genre"] or "outros", []).append(row)

    for genre in by_genre:
        by_genre[genre].sort(key=distance)

    ranked_genres = sorted(by_genre.items(), key=lambda kv: distance(kv[1][0]))

    result = []
    for genre, genre_rows in ranked_genres[:genres_limit]:
        result.extend(dict(r) for r in genre_rows[:per_genre])
    return result
