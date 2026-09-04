"""Testes do motor de matching.

_extract_target e find_tracks_by_genre sao funcoes puras sobre dados fixos -
o caso mais facil de testar que existe, e exatamente onde uma regressao
passaria despercebida (o app continua respondendo 200, so recomendando
errado). Sem isso, mexer no KEYWORD_MAP vira aposta.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from matching.engine import (  # noqa: E402
    DEFAULT_TARGET, KEYWORD_MAP, _extract_target, _is_negated, _normalize,
    find_tracks, find_tracks_by_genre,
)


# --------------------------------------------------------- normalizacao
def test_normalize_remove_acentos_e_caixa():
    assert _normalize("ÂNSIA") == "ansia"
    assert _normalize("Coração") == "coracao"


def test_normalize_torna_acentuado_equivalente():
    assert _normalize("ânsia") == _normalize("ansia")


# --------------------------------------------------------- alvo basico
def test_sem_keyword_cai_no_alvo_neutro():
    assert _extract_target("xyzzy plugh") == DEFAULT_TARGET


def test_keyword_simples_retorna_o_proprio_vetor():
    assert _extract_target("to muito triste") == KEYWORD_MAP["trist"]


def test_keyword_pega_flexoes_pelo_radical():
    # o ponto de usar radicais em vez de palavras completas
    assert _extract_target("tristeza") == KEYWORD_MAP["trist"]
    assert _extract_target("entristecido") == KEYWORD_MAP["trist"]


def test_acento_na_entrada_nao_impede_o_match():
    assert _extract_target("com ânsia") == KEYWORD_MAP["ansi"]


def test_mood_composto_tira_a_media_dos_vetores():
    # "triste mas quero dancar" deve cair ENTRE as duas regioes
    v, e = _extract_target("triste mas quero dancar")
    v_trist, e_trist = KEYWORD_MAP["trist"]
    v_danc, e_danc = KEYWORD_MAP["danc"]
    assert v == pytest.approx((v_trist + v_danc) / 2)
    assert e == pytest.approx((e_trist + e_danc) / 2)
    assert v_trist < v < v_danc


# --------------------------------------------------------- negacao
def test_negacao_inverte_o_vetor():
    v, e = _extract_target("nao quero nada triste")
    v_trist, e_trist = KEYWORD_MAP["trist"]
    assert v == pytest.approx(1.0 - v_trist)
    assert e == pytest.approx(1.0 - e_trist)


def test_negacao_leva_pro_lado_oposto_do_plano():
    # o comportamento que importa: pedir "nada triste" nao pode devolver
    # valence baixo. Esta era a falha mais visivel do matching.
    v_neg, _ = _extract_target("nada triste")
    v_pos, _ = _extract_target("triste")
    assert v_neg > 0.5 > v_pos


@pytest.mark.parametrize("frase", [
    "nao quero nada triste",
    "sem musica triste",
    "menos triste por favor",
    "evitar triste",
    "nem triste nem lenta",
])
def test_variacoes_de_negador(frase):
    v, _ = _extract_target(frase)
    assert v > 0.5, f"'{frase}' deveria inverter o vetor de tristeza"


def test_sem_negador_nao_inverte():
    assert _extract_target("quero algo triste") == KEYWORD_MAP["trist"]


def test_negador_distante_nao_afeta():
    # "nao" a mais de NEGATION_WINDOW tokens nao pertence a esta keyword
    assert _extract_target("nao aguento mais essa vida, so tristeza") == KEYWORD_MAP["trist"]


def test_negacao_afeta_so_a_keyword_negada():
    # "sem" nega "trist", mas "danc" continua positiva
    v, e = _extract_target("sem nada triste, quero dancar")
    v_trist, e_trist = KEYWORD_MAP["trist"]
    v_danc, e_danc = KEYWORD_MAP["danc"]
    assert v == pytest.approx(((1 - v_trist) + v_danc) / 2)
    assert e == pytest.approx(((1 - e_trist) + e_danc) / 2)


def test_is_negated_isolado():
    # posicao = indice onde a keyword COMECA
    assert _is_negated("nao quero nada trist", 15) is True
    assert _is_negated("quero muito trist", 12) is False


def test_janela_para_na_keyword_anterior():
    # o negador ja se aplicou a 'trist'; nao pode alcancar a proxima keyword
    texto = "sem nada triste, quero dancar"
    assert _is_negated(texto, texto.index("trist")) is True
    assert _is_negated(texto, texto.index("danc")) is False


def test_virgula_nao_gruda_o_negador_no_token():
    # "sem," precisa ser reconhecido como negador mesmo colado na pontuacao
    assert _is_negated("sem, trist", 5) is True


# --------------------------------------------------------- ranking
def test_find_tracks_respeita_o_limite():
    assert len(find_tracks("triste", limit=5)) == 5


def test_find_tracks_ordena_por_proximidade():
    tracks = find_tracks("festa", limit=10)
    alvo_v, alvo_e = _extract_target("festa")
    dists = [
        ((t["valence"] - alvo_v) ** 2 + (t["energy"] - alvo_e) ** 2) ** 0.5
        for t in tracks
    ]
    assert dists == sorted(dists)


def test_moods_opostos_devolvem_conjuntos_diferentes():
    calmo = {t["id"] for t in find_tracks("relaxar", limit=10)}
    festa = {t["id"] for t in find_tracks("festa", limit=10)}
    assert len(calmo & festa) < 5, "moods opostos nao deveriam se sobrepor tanto"


def test_negacao_muda_o_resultado_do_ranking():
    # teste de ponta a ponta da feature: nao basta o vetor mudar,
    # as faixas retornadas tem que mudar junto
    triste = {t["id"] for t in find_tracks("triste", limit=10)}
    nada_triste = {t["id"] for t in find_tracks("nao quero nada triste", limit=10)}
    assert triste != nada_triste


# --------------------------------------------------- diversificacao
def test_by_genre_respeita_o_teto_de_faixas():
    tracks = find_tracks_by_genre("triste", genres_limit=8, per_genre=6)
    assert len(tracks) <= 48


def test_by_genre_nao_deixa_um_genero_estourar_o_teto():
    tracks = find_tracks_by_genre("triste", genres_limit=8, per_genre=6)
    por_genero = {}
    for t in tracks:
        por_genero[t["genre"]] = por_genero.get(t["genre"], 0) + 1
    assert max(por_genero.values()) <= 6


def test_by_genre_diversifica_mais_que_o_ranking_global():
    # a razao de find_tracks_by_genre existir: sem ela, um genero domina
    plano = len({t["genre"] for t in find_tracks("triste", limit=20)})
    por_genero = len({t["genre"] for t in find_tracks_by_genre("triste", 8, 6)})
    assert por_genero >= plano


def test_by_genre_nao_repete_faixa():
    tracks = find_tracks_by_genre("animado", genres_limit=8, per_genre=6)
    ids = [t["id"] for t in tracks]
    assert len(ids) == len(set(ids))


def test_by_genre_e_deterministico():
    a = [t["id"] for t in find_tracks_by_genre("saudade", 8, 6)]
    b = [t["id"] for t in find_tracks_by_genre("saudade", 8, 6)]
    assert a == b
