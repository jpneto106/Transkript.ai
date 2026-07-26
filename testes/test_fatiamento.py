"""Testes do fatiamento de áudio (nucleo.fatiamento).

Extraídos dos invariantes de ``test_motores.py`` para a Etapa 1 do plano
``ol-um-outro-agente-graceful-oasis.md`` — agora que a lógica de corte vive
em ``nucleo/fatiamento``, este módulo a testa diretamente, sem precisar do
motor.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nucleo.fatiamento import (
    BUSCA_SILENCIO_SEGUNDOS,
    JANELA_SEGUNDOS_PADRAO,
    _ponto_mais_silencioso,
    fatiar,
    fatiar_por_silencio,
    fatiar_por_vad,
)

TAXA = 16000


def _ruido(segundos: float, volume: float = 0.5):
    """Áudio sintético com volume constante (nenhuma pausa)."""
    return np.full(int(segundos * TAXA), volume, dtype=np.float32)


# ----------------------------------------------------------------- silêncio

def test_audio_curto_nao_e_dividido():
    amostras = _ruido(30)
    assert fatiar_por_silencio(amostras, TAXA) == [(0, len(amostras))]


def test_nenhum_pedaco_ultrapassa_o_limite():
    """A garantia central: o modelo nunca recebe mais do que aguenta."""
    amostras = _ruido(JANELA_SEGUNDOS_PADRAO * 4.5)
    limite = int(JANELA_SEGUNDOS_PADRAO * TAXA)
    for _, fim in fatiar_por_silencio(amostras, TAXA):
        assert fim - _ <= limite


def test_fala_continua_sem_pausa_ainda_e_dividida():
    """Se não houver silêncio nenhum, o corte acontece do mesmo jeito."""
    amostras = _ruido(JANELA_SEGUNDOS_PADRAO * 2.5)
    pedacos = fatiar_por_silencio(amostras, TAXA)
    assert len(pedacos) >= 3


def test_pedacos_cobrem_todo_o_audio_sem_buraco():
    amostras = _ruido(JANELA_SEGUNDOS_PADRAO * 3.2)
    pedacos = fatiar_por_silencio(amostras, TAXA)
    assert pedacos[0][0] == 0
    assert pedacos[-1][1] == len(amostras)
    for (_, fim), (inicio_seguinte, _) in zip(pedacos, pedacos[1:]):
        assert fim == inicio_seguinte  # sem lacuna e sem sobreposição


def test_corta_na_pausa_quando_existe_uma():
    """Com um silêncio dentro da janela de busca, o corte deve cair nele."""
    amostras = _ruido(JANELA_SEGUNDOS_PADRAO * 2)
    quieto_em = int((JANELA_SEGUNDOS_PADRAO - 4) * TAXA)
    amostras[quieto_em : quieto_em + TAXA] = 0.0

    primeiro_fim = fatiar_por_silencio(amostras, TAXA)[0][1]
    assert abs(primeiro_fim - (quieto_em + TAXA / 2)) < TAXA  # dentro do silêncio


def test_ponto_mais_silencioso_acha_o_trecho_quieto():
    amostras = _ruido(10)
    amostras[5 * TAXA : 5 * TAXA + TAXA // 2] = 0.0
    ponto = _ponto_mais_silencioso(amostras, 4 * TAXA, 7 * TAXA, TAXA)
    assert 5 * TAXA <= ponto <= 5 * TAXA + TAXA // 2


def test_parametros_personalizados_sao_respeitados():
    """Quem chama pode encurtar a janela para testes ou outros usos."""
    amostras = _ruido(60)
    pedacos = fatiar_por_silencio(amostras, TAXA, janela_segundos=20.0)
    limite = int(20.0 * TAXA)
    for inicio, fim in pedacos:
        assert fim - inicio <= limite
    assert len(pedacos) >= 3


# ------------------------------------------------------------------ API pública

def test_fatiar_padrao_e_silencio():
    """Quem só chama ``fatiar(a, t)`` sem dizer o modo usa silêncio."""
    amostras = _ruido(60)
    assert fatiar(amostras, TAXA) == fatiar_por_silencio(amostras, TAXA)


def test_fatiar_modo_desconhecido_levanta_erro():
    amostras = _ruido(10)
    with pytest.raises(ValueError, match="modo de fatiamento desconhecido"):
        fatiar(amostras, TAXA, modo="invalido")


# ----------------------------------------------------------------------- VAD

def test_fatiar_por_vad_sem_pacote_levanta_runtimeerror_com_instrucao():
    """Sem silero-vad instalado, o erro tem que dizer como instalar."""
    try:
        from importlib.util import find_spec
        if find_spec("silero_vad") is not None:
            pytest.skip("silero_vad instalado; pulando este teste")
    except (ImportError, ValueError):
        pass

    amostras = _ruido(10)
    with pytest.raises(RuntimeError, match="silero-vad"):
        fatiar_por_vad(amostras, TAXA)


def test_fatiar_com_modo_vad_sem_pacote_levanta_runtimeerror():
    """A mesma proteção através do ponto de entrada único."""
    try:
        from importlib.util import find_spec
        if find_spec("silero_vad") is not None:
            pytest.skip("silero_vad instalado; pulando este teste")
    except (ImportError, ValueError):
        pass

    amostras = _ruido(10)
    with pytest.raises(RuntimeError, match="silero-vad"):
        fatiar(amostras, TAXA, modo="vad")
