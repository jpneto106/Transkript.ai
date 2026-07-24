"""Constantes compartilhadas entre o CLI e a API."""

from __future__ import annotations

from pathlib import Path

EXTENSOES_SUPORTADAS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".opus",
}

MODELOS_DISPONIVEIS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
FORMATOS_DISPONIVEIS = ["txt", "srt", "vtt", "json"]

PASTA_ENTRADA_PADRAO = Path("entrada")
PASTA_SAIDA_PADRAO = "saida"
PASTA_DOWNLOADS = PASTA_ENTRADA_PADRAO / "_downloads"

FINALIZADORES_DE_FRASE = (".", "!", "?", "…")
