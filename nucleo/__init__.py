"""Núcleo compartilhado de transcrição (usado pelo CLI transcrever.py e pela API FastAPI).

Ao importar qualquer parte de `nucleo`, o workaround de DLLs da NVIDIA no Windows é
aplicado automaticamente — garantindo que a GPU funcione tanto no CLI quanto na API
sem que cada consumidor precise lembrar de chamá-lo.
"""

from __future__ import annotations

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
from .transcricao import EventoProgresso, carregar_modelo, transcrever_arquivo

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
    "montar_blocos",
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
