"""Detecção de GPU/CPU e o workaround de DLLs da NVIDIA no Windows."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _registrar_dlls_nvidia() -> None:
    """No Windows, as DLLs de cuBLAS/cuDNN instaladas via pip (nvidia-*-cu12) ficam
    dentro de site-packages e o ctranslate2 só as encontra se estiverem no PATH
    (os.add_dll_directory não é suficiente para os LoadLibrary internos dele)."""
    if os.name != "nt":
        return
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not base.is_dir():
        return
    pastas = [str(p) for p in base.glob("*/bin")]
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
