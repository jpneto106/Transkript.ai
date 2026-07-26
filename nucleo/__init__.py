"""Núcleo compartilhado de transcrição (usado pelo CLI transcrever.py e pela API FastAPI).

Ao importar qualquer parte de `nucleo`, o workaround de DLLs da NVIDIA no Windows é
aplicado automaticamente — garantindo que a GPU funcione tanto no CLI quanto na API
sem que cada consumidor precise lembrar de chamá-lo.
"""

from __future__ import annotations

import os

# --- App portátil: tudo dentro da pasta do programa ---
# A raiz é calculada em nucleo/caminhos.py, que também trata o caso do programa
# empacotado (PyInstaller), onde __file__ apontaria para dentro do pacote.
from .caminhos import RAIZ_APP as _APP_ROOT

# Modelos do Whisper ficam em <app>/modelos (em vez do cache compartilhado do sistema),
# tornando o programa autossuficiente. setdefault respeita um HF_HOME já definido.
os.environ.setdefault("HF_HOME", str(_APP_ROOT / "modelos"))

# ffmpeg embutido (se presente em <app>/ferramentas/ffmpeg/bin) tem prioridade no PATH,
# para o programa não depender de um ffmpeg instalado no sistema.
_FFMPEG_BIN = _APP_ROOT / "ferramentas" / "ffmpeg" / "bin"
if _FFMPEG_BIN.is_dir():
    os.environ["PATH"] = str(_FFMPEG_BIN) + os.pathsep + os.environ.get("PATH", "")

from .dispositivo import _registrar_dlls_nvidia

_registrar_dlls_nvidia()

from .blocos import extrair_palavras, montar_blocos
from .constantes import (
    EXTENSOES_SUPORTADAS,
    FINALIZADORES_DE_FRASE,
    FORMATOS_DISPONIVEIS,
    MODELOS_DISPONIVEIS,
    PASTA_DOWNLOADS,
    PASTA_ENTRADA_PADRAO,
    PASTA_SAIDA_PADRAO,
)
from .dispositivo import detectar_dispositivo
from .entrada import baixar_de_url, eh_url, encontrar_arquivos
from .escrita import escrever_saidas
from .formatacao import (
    Palavra,
    ResultadoTranscricao,
    Segmento,
    formatar_hms,
    formatar_timestamp_legenda,
)
from .diarizacao import (
    TurnoFalante,
    atribuir_falantes,
    carregar_pipeline,
    diarizacao_disponivel,
    diarizar_arquivo,
    rotulos_em_ordem,
)
from .midia import carregar_audio, duracao_segundos, informacoes
from .motores import (
    carregar_modelo_do_motor,
    motores_disponiveis,
    transcrever_com_motor,
)
from .transcricao import (
    EventoProgresso,
    TranscricaoCancelada,
    carregar_modelo,
    transcrever_arquivo,
)

__all__ = [
    "EXTENSOES_SUPORTADAS",
    "FINALIZADORES_DE_FRASE",
    "FORMATOS_DISPONIVEIS",
    "MODELOS_DISPONIVEIS",
    "PASTA_DOWNLOADS",
    "PASTA_ENTRADA_PADRAO",
    "PASTA_SAIDA_PADRAO",
    "Palavra",
    "ResultadoTranscricao",
    "Segmento",
    "EventoProgresso",
    "TranscricaoCancelada",
    "TurnoFalante",
    "atribuir_falantes",
    "carregar_audio",
    "carregar_modelo_do_motor",
    "carregar_pipeline",
    "motores_disponiveis",
    "transcrever_com_motor",
    "diarizacao_disponivel",
    "diarizar_arquivo",
    "duracao_segundos",
    "informacoes",
    "montar_blocos",
    "rotulos_em_ordem",
    "extrair_palavras",
    "detectar_dispositivo",
    "baixar_de_url",
    "eh_url",
    "encontrar_arquivos",
    "escrever_saidas",
    "formatar_hms",
    "formatar_timestamp_legenda",
    "carregar_modelo",
    "transcrever_arquivo",
]
