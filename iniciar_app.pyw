#!/usr/bin/env python3
"""Inicia o aplicativo desktop: sobe a API (uvicorn, em processo separado) e abre a
janela nativa (pywebview).

O servidor roda como um PROCESSO à parte (não uma thread) para não competir com a
thread da janela — isso evita o congelamento ("Não está respondendo") que acontecia
quando os dois disputavam o mesmo processo Python.

Duplo-clique em iniciar_app.bat chama este arquivo.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PASTA_LOG = RAIZ / "dados_app"
PASTA_LOG.mkdir(parents=True, exist_ok=True)
LOG = PASTA_LOG / "launcher.log"


def log(msg: str) -> None:
    linha = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def porta_livre() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


def iniciar_servidor(porta: int) -> subprocess.Popen:
    """Sobe uvicorn como processo separado, sem abrir janela de console."""
    log_servidor = open(PASTA_LOG / "servidor.log", "w", encoding="utf-8")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(porta),
        "--log-level",
        "warning",
    ]
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return subprocess.Popen(
        cmd,
        cwd=str(RAIZ),
        stdout=log_servidor,
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )


def esperar_servidor(url: str, tentativas: int = 200) -> bool:
    import requests

    for _ in range(tentativas):
        try:
            if requests.get(url + "api/saude", timeout=0.3).ok:
                return True
        except Exception:
            time.sleep(0.1)
    return False


def main() -> None:
    log("=== iniciando ===")
    porta = porta_livre()
    log(f"porta escolhida: {porta}")

    servidor = iniciar_servidor(porta)
    log(f"servidor iniciado (pid {servidor.pid})")

    url = f"http://127.0.0.1:{porta}/"
    if not esperar_servidor(url):
        log("ERRO: servidor não respondeu ao health check")
        try:
            servidor.terminate()
        except Exception:
            pass
        sys.exit(1)
    log("servidor respondeu ao health check")

    import webview

    class PontePython:
        def __init__(self) -> None:
            self.janela = None

        def escolher_arquivo(self):
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
            return list(resultado) if resultado else []

        def abrir_pasta(self, caminho: str) -> bool:
            try:
                os.startfile(caminho)  # type: ignore[attr-defined]
                return True
            except Exception:
                return False

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
    log("janela criada, abrindo interface")

    def ao_fechar() -> None:
        log("janela fechada, encerrando servidor")
        try:
            servidor.terminate()
        except Exception:
            pass

    janela.events.closed += ao_fechar

    try:
        webview.start()
    finally:
        try:
            servidor.terminate()
        except Exception:
            pass
    log("=== encerrado ===")


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    try:
        main()
    except Exception as erro:  # registra qualquer falha antes de morrer
        log(f"ERRO FATAL: {erro!r}")
        raise
