"""Testes do fatiamento de áudio longo para o motor NVIDIA.

Os modelos da NVIDIA têm um teto rígido de duração e, bem antes dele, ficam
desproporcionalmente lentos (medido: 240s levam 32s; 300s levam 172s; 420s
falham). Por isso o áudio é cortado em pedaços — preferindo pausas, mas sem
nunca ultrapassar o limite. Estes testes protegem exatamente essa garantia.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nucleo.motores import (
    _JANELA_SEGUNDOS,
    _fatiar_audio,
    _ponto_mais_silencioso,
    _tokens_para_palavras,
)

TAXA = 16000


def _ruido(segundos: float, volume: float = 0.5):
    """Áudio sintético com volume constante (nenhuma pausa)."""
    return np.full(int(segundos * TAXA), volume, dtype=np.float32)


# ------------------------------------------------------------------ fatiamento

def test_audio_curto_nao_e_dividido():
    amostras = _ruido(30)
    assert _fatiar_audio(amostras, TAXA) == [(0, len(amostras))]


def test_nenhum_pedaco_ultrapassa_o_limite():
    """A garantia central: o modelo nunca recebe mais do que aguenta."""
    amostras = _ruido(_JANELA_SEGUNDOS * 4.5)
    limite = int(_JANELA_SEGUNDOS * TAXA)
    for inicio, fim in _fatiar_audio(amostras, TAXA):
        assert fim - inicio <= limite


def test_fala_continua_sem_pausa_ainda_e_dividida():
    """Se não houver silêncio nenhum, o corte acontece do mesmo jeito."""
    amostras = _ruido(_JANELA_SEGUNDOS * 2.5)
    pedacos = _fatiar_audio(amostras, TAXA)
    assert len(pedacos) >= 3


def test_pedacos_cobrem_todo_o_audio_sem_buraco():
    amostras = _ruido(_JANELA_SEGUNDOS * 3.2)
    pedacos = _fatiar_audio(amostras, TAXA)
    assert pedacos[0][0] == 0
    assert pedacos[-1][1] == len(amostras)
    for (_, fim), (inicio_seguinte, _) in zip(pedacos, pedacos[1:]):
        assert fim == inicio_seguinte  # sem lacuna e sem sobreposição


def test_corta_na_pausa_quando_existe_uma():
    """Com um silêncio dentro da janela de busca, o corte deve cair nele."""
    amostras = _ruido(_JANELA_SEGUNDOS * 2)
    # Silêncio de 1s pouco antes do fim da primeira janela.
    quieto_em = int((_JANELA_SEGUNDOS - 4) * TAXA)
    amostras[quieto_em : quieto_em + TAXA] = 0.0

    primeiro_fim = _fatiar_audio(amostras, TAXA)[0][1]
    assert abs(primeiro_fim - (quieto_em + TAXA / 2)) < TAXA  # dentro do silêncio


def test_ponto_mais_silencioso_acha_o_trecho_quieto():
    amostras = _ruido(10)
    amostras[5 * TAXA : 5 * TAXA + TAXA // 2] = 0.0
    ponto = _ponto_mais_silencioso(amostras, 4 * TAXA, 7 * TAXA, TAXA)
    assert 5 * TAXA <= ponto <= 5 * TAXA + TAXA // 2


# ------------------------------------------------- tokens -> palavras inteiras

def test_junta_sub_tokens_em_palavras():
    """O modelo devolve pedaços ('  y','out','u','ber'); viram uma palavra só."""
    tokens = [" Um", " y", "out", "u", "ber", " ok"]
    tempos = [0.0, 0.4, 0.5, 0.6, 0.7, 1.2]
    palavras = _tokens_para_palavras(tokens, tempos, 2.0)
    assert [p.texto for p in palavras] == [" Um", " youtuber", " ok"]
    assert palavras[0].inicio == 0.0
    assert palavras[1].inicio == 0.4
    assert palavras[-1].fim == 2.0


def test_nenhuma_palavra_com_tempo_invertido():
    tokens = [" a", " b", " c"]
    tempos = [1.0, 1.0, 1.0]  # timestamps repetidos, caso degenerado
    for palavra in _tokens_para_palavras(tokens, tempos, 1.0):
        assert palavra.fim >= palavra.inicio


def test_lista_vazia_nao_quebra():
    assert _tokens_para_palavras([], [], 5.0) == []
