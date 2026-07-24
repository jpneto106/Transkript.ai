#!/usr/bin/env python3
"""Inicia o aplicativo desktop: sobe a API (uvicorn) e abre a janela nativa (pywebview).

Duplo-clique em iniciar_app.bat chama este arquivo. A extensão .pyw evita abrir
um terminal preto junto com a janela.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

# Importar o núcleo aplica o workaround de DLLs da NVIDIA antes de qualquer coisa.
import nucleo  # noqa: F401

import requests
import uvicorn
import webview

from api.main import criar_app


def _porta_livre() -> int:
    """Pede ao SO uma porta TCP livre em 127.0.0.1 (evita colisão de porta)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


class PontePython:
    """Métodos expostos ao JavaScript da interface (window.pywebview.api.*)."""

    def __init__(self) -> None:
        self.janela: webview.Window | None = None

    def escolher_arquivo(self) -> list[str]:
        if self.janela is None:
            return []
        resultado = self.janela.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=(
                "Vídeos e áudios (*.mp4;*.mkv;*.mov;*.avi;*.webm;*.mp3;*.wav;*.m4a;*.flac;*.ogg)",
                "Todos os arquivos (*.*)",
            ),
        )
        if not resultado:
            return []
        return list(resultado)

    def abrir_pasta(self, caminho: str) -> bool:
        try:
            os.startfile(caminho)  # type: ignore[attr-defined]  # Windows
            return True
        except Exception:
            return False


def _esperar_servidor(url: str, tentativas: int = 150) -> bool:
    """Espera ativamente o /api/saude responder antes de abrir a janela."""
    for _ in range(tentativas):
        try:
            if requests.get(url + "api/saude", timeout=0.3).ok:
                return True
        except Exception:
            time.sleep(0.05)
    return False


def main() -> None:
    porta = _porta_livre()
    app = criar_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning")
    servidor = uvicorn.Server(config)

    thread = threading.Thread(target=servidor.run, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{porta}/"
    if not _esperar_servidor(url):
        # Sem servidor não há o que exibir; encerra silenciosamente.
        servidor.should_exit = True
        sys.exit(1)

    ponte = PontePython()
    janela = webview.create_window(
        "Transcritor de Vídeos e Áudios",
        url,
        width=1180,
        height=820,
        min_size=(940, 640),
        js_api=ponte,
    )
    ponte.janela = janela

    def ao_fechar() -> None:
        servidor.should_exit = True

    janela.events.closed += ao_fechar
    webview.start()


if __name__ == "__main__":
    # Garante que o diretório do projeto está no sys.path (para achar api/ e nucleo/).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
