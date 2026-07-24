"""Testes de montar_blocos e extrair_palavras (nucleo.blocos)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nucleo.blocos import extrair_palavras, montar_blocos
from nucleo.formatacao import Palavra


def _palavras(textos_com_tempo):
    """Ajuda a criar palavras a partir de (texto, inicio, fim)."""
    return [Palavra(inicio=i, fim=f, texto=t) for (t, i, f) in textos_com_tempo]


def test_corte_por_caracteres():
    # max_caracteres pequeno força vários blocos mesmo sem pontuação.
    palavras = _palavras([
        (" um", 0.0, 0.5),
        (" dois", 0.5, 1.0),
        (" tres", 1.0, 1.5),
        (" quatro", 1.5, 2.0),
        (" cinco", 2.0, 2.5),
    ])
    blocos = montar_blocos(palavras, max_caracteres=10, max_duracao=100.0)
    assert len(blocos) >= 2
    for b in blocos:
        assert len(b.texto) <= 12  # tolera a palavra que estoura o limite ao ser adicionada


def test_corte_por_duracao():
    # Blocos com muitos segundos devem ser quebrados por duração.
    palavras = _palavras([
        (" a", 0.0, 2.0),
        (" b", 2.0, 4.0),
        (" c", 4.0, 6.0),
        (" d", 6.0, 8.0),
    ])
    blocos = montar_blocos(palavras, max_caracteres=1000, max_duracao=3.0)
    assert len(blocos) >= 2
    for b in blocos:
        assert (b.fim - b.inicio) <= 4.0


def test_corte_por_pontuacao():
    # Ao encontrar ponto final com tamanho razoável (> 40% do limite), fecha o bloco.
    # Com max_caracteres=20, o limiar é 8; "Ola mundo." (10) o ultrapassa e fecha ali.
    palavras = _palavras([
        (" Ola", 0.0, 0.5),
        (" mundo.", 0.5, 1.0),
        (" Tudo", 1.0, 1.5),
        (" bem?", 1.5, 2.0),
    ])
    blocos = montar_blocos(palavras, max_caracteres=20, max_duracao=100.0)
    assert len(blocos) == 2
    assert blocos[0].texto == "Ola mundo."
    assert blocos[1].texto == "Tudo bem?"


def test_pontuacao_curta_nao_corta():
    # Pontuação com bloco ainda curto (< 40% do limite) NÃO deve cortar.
    palavras = _palavras([
        (" Ola", 0.0, 0.5),
        (" mundo.", 0.5, 1.0),
        (" Tudo", 1.0, 1.5),
        (" bem?", 1.5, 2.0),
    ])
    blocos = montar_blocos(palavras, max_caracteres=80, max_duracao=100.0)
    assert len(blocos) == 1
    assert blocos[0].texto == "Ola mundo. Tudo bem?"


def test_inicio_e_fim_do_bloco():
    palavras = _palavras([
        (" primeira", 1.0, 1.4),
        (" segunda", 1.4, 2.2),
    ])
    blocos = montar_blocos(palavras, max_caracteres=80, max_duracao=100.0)
    assert len(blocos) == 1
    assert blocos[0].inicio == 1.0
    assert blocos[0].fim == 2.2


def test_lista_vazia():
    assert montar_blocos([], max_caracteres=80, max_duracao=6.0) == []


class _SegFalso:
    def __init__(self, start, end, text, words=None):
        self.start = start
        self.end = end
        self.text = text
        self.words = words


class _PalavraFalsa:
    def __init__(self, start, end, word):
        self.start = start
        self.end = end
        self.word = word


def test_extrair_palavras_com_words():
    seg = _SegFalso(0.0, 1.0, "oi mundo", words=[
        _PalavraFalsa(0.0, 0.4, " oi"),
        _PalavraFalsa(0.4, 1.0, " mundo"),
    ])
    palavras = extrair_palavras([seg])
    assert [p.texto for p in palavras] == [" oi", " mundo"]


def test_extrair_palavras_sem_words_usa_segmento():
    seg = _SegFalso(0.0, 2.0, "texto inteiro", words=None)
    palavras = extrair_palavras([seg])
    assert len(palavras) == 1
    assert palavras[0].texto == " texto inteiro"
