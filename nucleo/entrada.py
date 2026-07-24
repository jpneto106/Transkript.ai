"""Resolução das entradas do usuário: arquivos locais, pastas e links (URLs)."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Callable

from .constantes import EXTENSOES_SUPORTADAS, PASTA_DOWNLOADS


def eh_url(texto: str) -> bool:
    return texto.startswith("http://") or texto.startswith("https://")


def baixar_de_url(url: str, pasta_destino: Path) -> Path:
    import yt_dlp

    pasta_destino.mkdir(parents=True, exist_ok=True)
    opcoes = {
        "format": "bestaudio/best",
        "outtmpl": str(pasta_destino / "%(title).150B [%(id)s].%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "restrictfilenames": False,
    }
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info))


def encontrar_arquivos(
    entradas: list[str],
    pasta_downloads: Path = PASTA_DOWNLOADS,
    *,
    notificar: Callable[[str, str], None] | None = None,
    contexto_download: Callable[[str], contextlib.AbstractContextManager] | None = None,
) -> list[Path]:
    """Resolve a lista de entradas em caminhos de arquivo concretos.

    - 'notificar(nivel, mensagem)': callback opcional para avisos/erros (nivel:
      "info" | "aviso" | "erro"). Substitui os prints diretos que o CLI fazia.
    - 'contexto_download(mensagem)': callback opcional que devolve um context manager
      exibido enquanto uma URL é baixada (o CLI passa console.status; a API não passa).
    """

    def _notificar(nivel: str, mensagem: str) -> None:
        if notificar is not None:
            notificar(nivel, mensagem)

    def _contexto(mensagem: str) -> contextlib.AbstractContextManager:
        if contexto_download is not None:
            return contexto_download(mensagem)
        return contextlib.nullcontext()

    arquivos: list[Path] = []
    for entrada in entradas:
        if eh_url(entrada):
            with _contexto(f"Baixando vídeo de: {entrada}"):
                try:
                    caminho = baixar_de_url(entrada, pasta_downloads)
                except Exception as erro:
                    _notificar("erro", f"Erro ao baixar '{entrada}': {erro}")
                    continue
            _notificar("info", f"Baixado: {caminho.name}")
            arquivos.append(caminho)
            continue

        caminho = Path(entrada)
        if caminho.is_dir():
            for item in sorted(caminho.rglob("*")):
                if item.is_file() and item.suffix.lower() in EXTENSOES_SUPORTADAS:
                    arquivos.append(item)
        elif caminho.is_file():
            arquivos.append(caminho)
        else:
            _notificar("aviso", f"'{entrada}' não encontrado, ignorando.")
    return arquivos
