"""Descobre a pasta raiz do programa — funcionando também quando empacotado.

Por que este módulo existe
--------------------------
Rodando a partir do código-fonte, a raiz é simplesmente a pasta que contém
`nucleo/` e `api/`, e `Path(__file__).parent.parent` resolve isso.

Dentro de um executável do PyInstaller, porém, `__file__` aponta para **dentro
do pacote** (`servidor/_internal/...`). Usar aquele cálculo faria os modelos, o
banco de dados e as transcrições nascerem escondidos nas entranhas do programa
— lugares que o desinstalador não varre. Como "desinstalar sem deixar rastro" é
requisito do projeto, a raiz precisa ser sempre a pasta visível do aplicativo.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Nome da variável de ambiente que a casca usa para informar a raiz.
VARIAVEL_RAIZ = "TRANSKRIPT_RAIZ"


def descobrir_raiz() -> Path:
    """Devolve a pasta do aplicativo (onde ficam modelos/, dados/, saida/...)."""

    # 1. Alguém disse explicitamente onde é — é o que a casca faz ao subir o
    #    servidor. É o caminho mais confiável, então vem primeiro.
    definida = os.environ.get(VARIAVEL_RAIZ)
    if definida:
        return Path(definida).resolve()

    # 2. Empacotado: o executável mora em <raiz>/servidor/servidor.exe.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent

    # 3. Código-fonte: a pasta que contém nucleo/ e api/.
    return Path(__file__).resolve().parent.parent


#: Raiz do aplicativo, calculada uma única vez na importação.
RAIZ_APP = descobrir_raiz()
