"""Leitura de metadados de mídia (duração) com o ffprobe embutido.

Serve para mostrar ao usuário a duração do vídeo/áudio assim que ele escolhe o
arquivo — antes de transcrever, para ele conferir que pegou o arquivo certo.

Usamos o ffprobe (que vem junto do ffmpeg em <app>/ferramentas/ffmpeg/bin, já
colocado no PATH por nucleo/__init__.py) em vez de ler a duração no navegador:
o navegador não abre mkv, avi e vários outros formatos que o programa aceita.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# No Windows, evita o piscar de uma janela de console preta a cada chamada.
_SEM_JANELA = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined]

_TEMPO_LIMITE_SEGUNDOS = 30


def duracao_segundos(arquivo: Path) -> float | None:
    """Duração do áudio/vídeo em segundos, ou None se não for possível ler.

    Nunca levanta exceção: a duração é um extra de conveniência na interface e
    não pode impedir o usuário de transcrever um arquivo que o Whisper leria bem.
    """
    if not arquivo.is_file():
        return None

    try:
        processo = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(arquivo),
            ],
            capture_output=True,
            text=True,
            timeout=_TEMPO_LIMITE_SEGUNDOS,
            creationflags=_SEM_JANELA,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if processo.returncode != 0:
        return None

    try:
        dados = json.loads(processo.stdout or "{}")
        bruto = dados.get("format", {}).get("duration")
        if bruto is None:
            return None
        duracao = float(bruto)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    # Alguns arquivos declaram duração 0 ou negativa; tratamos como desconhecida.
    return duracao if duracao > 0 else None


def informacoes(arquivo: Path) -> dict[str, object]:
    """Dados do arquivo úteis para a interface antes de transcrever."""
    existe = arquivo.is_file()
    return {
        "nome": arquivo.name,
        "existe": existe,
        "tamanho_bytes": arquivo.stat().st_size if existe else None,
        "duracao_segundos": duracao_segundos(arquivo) if existe else None,
    }
