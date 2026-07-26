"""Detecção de GPU/CPU e o workaround de DLLs da NVIDIA no Windows."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .caminhos import RAIZ_APP


def _pastas_dlls_nvidia() -> list[str]:
    """Onde procurar as DLLs de cuBLAS/cuDNN, nas duas formas de rodar o programa.

    Empacotado, elas ficam em <app>/ferramentas/cuda — mesmo padrão do ffmpeg
    embutido, e dentro da pasta do programa, para o desinstalador levar tudo.
    A partir do código-fonte, vêm dos pacotes pip nvidia-*-cu12 no venv.
    """
    embutidas = RAIZ_APP / "ferramentas" / "cuda"
    if embutidas.is_dir():
        pastas = [str(p) for p in embutidas.glob("*/bin") if p.is_dir()]
        if pastas:
            return pastas

    do_venv = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if do_venv.is_dir():
        pastas = [str(p) for p in do_venv.glob("*/bin") if p.is_dir()]
        if pastas:
            return pastas

    # O PyTorch (instalado junto com a identificação de falantes) traz as suas
    # próprias cópias de cuDNN/cuBLAS, e elas servem para o ctranslate2 também.
    # Sem isto, o programa empacotado cairia para o processador em silêncio —
    # justamente o tipo de falha muda que mais custa a diagnosticar.
    for base in _bases_de_busca():
        biblioteca_torch = base / "torch" / "lib"
        if biblioteca_torch.is_dir() and any(biblioteca_torch.glob("cudnn*.dll")):
            return [str(biblioteca_torch)]

    return []


def _bases_de_busca() -> list[Path]:
    """Onde procurar pacotes Python: no pacote empacotado e no ambiente normal."""
    bases: list[Path] = []
    interno = getattr(sys, "_MEIPASS", None)
    if interno:
        bases.append(Path(interno))
    bases.append(Path(sys.executable).resolve().parent / "_internal")
    bases.append(Path(sys.prefix) / "Lib" / "site-packages")
    return [b for b in bases if b.is_dir()]


def _registrar_dlls_nvidia() -> None:
    """No Windows, o ctranslate2 só encontra as DLLs de cuBLAS/cuDNN se elas
    estiverem no PATH (os.add_dll_directory não basta para os LoadLibrary
    internos dele)."""
    if os.name != "nt":
        return
    pastas = _pastas_dlls_nvidia()
    if pastas:
        os.environ["PATH"] = os.pathsep.join(pastas) + os.pathsep + os.environ.get("PATH", "")


def detectar_dispositivo(preferencia: str, notificar=None) -> tuple[str, str]:
    """Decide device/compute_type para o ctranslate2, respeitando preferência do usuário.

    'notificar' é um callback opcional (nivel, mensagem) para avisar, por exemplo,
    quando a GPU foi pedida mas não está disponível. Se None, nada é reportado.
    """
    if preferencia == "cpu":
        return "cpu", "int8"

    dispositivo = "cpu"
    if preferencia in ("auto", "cuda"):
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                dispositivo = "cuda"
        except Exception:
            dispositivo = "cpu"

    if preferencia == "cuda" and dispositivo != "cuda" and notificar is not None:
        notificar("aviso", "GPU CUDA não encontrada, usando CPU.")

    compute_type = "float16" if dispositivo == "cuda" else "int8"
    return dispositivo, compute_type
