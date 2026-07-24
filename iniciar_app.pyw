#!/usr/bin/env python3
"""Inicia o aplicativo desktop: sobe a API (uvicorn, em processo separado) e abre a
janela nativa (pywebview).

Dois cuidados importantes contra travamentos:
- O servidor roda como PROCESSO à parte (não thread), para não competir com a janela.
- O processo do servidor é amarrado a um "Job Object" do Windows com KILL_ON_JOB_CLOSE:
  se este launcher morrer (inclusive fechado à força), o servidor morre junto — assim
  não sobram processos órfãos acumulando e deixando tudo lento.
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
sys.path.insert(0, str(RAIZ))

from api.configuracao import PASTA_DADOS  # noqa: E402  (define a pasta de dados/logs)

PASTA_DADOS.mkdir(parents=True, exist_ok=True)
LOG = PASTA_DADOS / "launcher.log"

_job_handle = None  # mantém o Job Object vivo enquanto o launcher existir


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


def _amarrar_ao_job(proc: subprocess.Popen) -> None:
    """Amarra o processo a um Job Object que mata o filho se este launcher morrer."""
    if os.name != "nt":
        return
    global _job_handle
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        JobObjectExtendedLimitInformation = 9
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        # int(proc._handle) é o HANDLE do processo criado pelo Popen.
        kernel32.AssignProcessToJobObject(job, int(proc._handle))
        _job_handle = job
        log("servidor amarrado ao Job Object (morre junto com o launcher)")
    except Exception as erro:
        log(f"aviso: não consegui amarrar ao Job Object: {erro!r}")


def iniciar_servidor(porta: int) -> subprocess.Popen:
    log_servidor = open(PASTA_DADOS / "servidor.log", "w", encoding="utf-8")
    cmd = [
        sys.executable, "-m", "uvicorn", "api.main:app",
        "--host", "127.0.0.1", "--port", str(porta), "--log-level", "warning",
    ]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined]
    proc = subprocess.Popen(
        cmd, cwd=str(RAIZ), stdout=log_servidor, stderr=subprocess.STDOUT, creationflags=flags
    )
    _amarrar_ao_job(proc)
    return proc


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
        "Transcritor de Vídeos e Áudios", url,
        width=1180, height=820, min_size=(940, 640), js_api=ponte,
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
    try:
        main()
    except Exception as erro:
        log(f"ERRO FATAL: {erro!r}")
        raise
