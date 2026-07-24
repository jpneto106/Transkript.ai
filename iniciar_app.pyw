#!/usr/bin/env python3
"""Inicia o aplicativo desktop.

Sobe a API (uvicorn) como PROCESSO separado e abre a interface numa janela do
Microsoft Edge em "modo aplicativo" (--app): uma janela limpa, sem barra de
navegador, com aparência de programa nativo — mas usando o motor robusto do Edge,
sem os travamentos que o pywebview causava nesta máquina.

O processo do servidor é amarrado a um Job Object do Windows (KILL_ON_JOB_CLOSE):
se este launcher morrer, o servidor morre junto (sem processos órfãos).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from api.configuracao import PASTA_DADOS  # noqa: E402

PASTA_DADOS.mkdir(parents=True, exist_ok=True)
LOG = PASTA_DADOS / "launcher.log"

_job_handle = None


def log(msg: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def porta_livre() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


def _amarrar_ao_job(proc: subprocess.Popen) -> None:
    if os.name != "nt":
        return
    global _job_handle
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

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

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
        kernel32.AssignProcessToJobObject(job, int(proc._handle))
        _job_handle = job
        log("servidor amarrado ao Job Object")
    except Exception as erro:
        log(f"aviso: Job Object falhou: {erro!r}")


def iniciar_servidor(porta: int) -> subprocess.Popen:
    log_servidor = open(PASTA_DADOS / "servidor.log", "w", encoding="utf-8")
    cmd = [sys.executable, "-m", "uvicorn", "api.main:app",
           "--host", "127.0.0.1", "--port", str(porta), "--log-level", "warning"]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined]
    proc = subprocess.Popen(cmd, cwd=str(RAIZ), stdout=log_servidor,
                            stderr=subprocess.STDOUT, creationflags=flags)
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


def _achar_edge() -> str | None:
    candidatos = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidatos:
        if Path(c).is_file():
            return c
    achado = shutil.which("msedge")
    return achado


def abrir_janela(url: str) -> subprocess.Popen | None:
    """Abre o Edge em modo app (janela limpa, sem barra do navegador).

    Usa um perfil próprio (--user-data-dir) para garantir que este é um processo
    novo e independente — assim conseguimos esperar ele fechar e derrubar o servidor.
    Retorna o processo do Edge, ou None se abriu no navegador padrão (fallback)."""
    edge = _achar_edge()
    perfil = PASTA_DADOS / "janela"
    perfil.mkdir(parents=True, exist_ok=True)
    if edge:
        cmd = [
            edge,
            f"--app={url}",
            f"--user-data-dir={perfil}",
            "--window-size=1180,840",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        log(f"abrindo Edge em modo app: {edge}")
        return subprocess.Popen(cmd)
    log("Edge não encontrado; abrindo no navegador padrão")
    webbrowser.open(url)
    return None


def main() -> None:
    log("=== iniciando ===")
    porta = porta_livre()
    log(f"porta: {porta}")

    servidor = iniciar_servidor(porta)
    log(f"servidor pid {servidor.pid}")

    url = f"http://127.0.0.1:{porta}/"
    if not esperar_servidor(url):
        log("ERRO: servidor não respondeu")
        try:
            servidor.terminate()
        except Exception:
            pass
        sys.exit(1)
    log("servidor pronto")

    janela = abrir_janela(url)

    try:
        if janela is not None:
            # Espera a janela do Edge (modo app) fechar; então derruba o servidor.
            janela.wait()
            log("janela do Edge fechada")
        else:
            # Fallback (navegador padrão): sem processo para esperar; mantém o
            # servidor vivo até o usuário fechar este launcher.
            log("modo fallback: servidor rodando; feche esta janela para encerrar")
            while servidor.poll() is None:
                time.sleep(1)
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
