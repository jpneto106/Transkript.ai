"""Testes da descoberta da pasta raiz do aplicativo.

A raiz decide onde ficam modelos, banco, saídas e a interface. Errar aqui não
gera exceção — gera um 404 misterioso ou modelos baixados no lugar errado, que
o desinstalador depois não encontra. Daí valer testes próprios.
"""

from __future__ import annotations

import sys
from pathlib import Path

import servidor
from nucleo.caminhos import VARIAVEL_RAIZ, descobrir_raiz

RAIZ_REPO = Path(__file__).resolve().parent.parent


def test_nome_da_variavel_igual_no_servidor():
    """servidor.py duplica o nome da variável de propósito (ordem de importação).

    Se um dos dois for renomeado sem o outro, a casca passaria a raiz por um
    nome que ninguém lê — e o servidor cairia num caminho errado em silêncio.
    """
    assert servidor.VARIAVEL_RAIZ == VARIAVEL_RAIZ


def test_variavel_de_ambiente_tem_prioridade(monkeypatch, tmp_path):
    """É assim que a casca informa onde o aplicativo foi instalado."""
    monkeypatch.setenv(VARIAVEL_RAIZ, str(tmp_path))
    assert descobrir_raiz() == tmp_path.resolve()


def test_sem_variavel_usa_a_pasta_do_projeto(monkeypatch):
    """Rodando a partir do código-fonte, a raiz é a pasta que contém nucleo/."""
    monkeypatch.delenv(VARIAVEL_RAIZ, raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert descobrir_raiz() == RAIZ_REPO


def test_empacotado_usa_a_pasta_acima_do_executavel(monkeypatch, tmp_path):
    """Empacotado, o executável mora em <raiz>/servidor/servidor.exe.

    Sem este tratamento a raiz cairia dentro do próprio pacote, escondendo
    modelos e banco de dados onde o desinstalador não varre.
    """
    monkeypatch.delenv(VARIAVEL_RAIZ, raising=False)
    pasta_servidor = tmp_path / "servidor"
    pasta_servidor.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(pasta_servidor / "servidor.exe"))
    assert descobrir_raiz() == tmp_path.resolve()
