"""Constantes compartilhadas entre o CLI e a API."""

from __future__ import annotations

from pathlib import Path

EXTENSOES_SUPORTADAS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".opus",
}

# --- Catálogo de modelos de transcrição -------------------------------------
# O programa aceita motores diferentes. O nome interno do modelo é único em todo
# o catálogo, então basta ele para descobrir qual motor usar e de onde baixar.

MOTOR_WHISPER = "whisper"
MOTOR_NVIDIA = "nvidia"

#: nome interno -> (motor, repositório no Hugging Face)
CATALOGO_MODELOS: dict[str, tuple[str, str]] = {
    # Whisper (faster-whisper) — o motor original do programa.
    "tiny":         (MOTOR_WHISPER, "Systran/faster-whisper-tiny"),
    "base":         (MOTOR_WHISPER, "Systran/faster-whisper-base"),
    "small":        (MOTOR_WHISPER, "Systran/faster-whisper-small"),
    "medium":       (MOTOR_WHISPER, "Systran/faster-whisper-medium"),
    "large-v2":     (MOTOR_WHISPER, "Systran/faster-whisper-large-v2"),
    "large-v3":     (MOTOR_WHISPER, "Systran/faster-whisper-large-v3"),
    # NVIDIA (NeMo) rodados em ONNX. O repositório é a conversão para ONNX, e
    # não o oficial da NVIDIA — é dela que a biblioteca baixa. Mesma licença
    # aberta do original (CC-BY-4.0). Alguns entendem português, outros só
    # inglês; o idioma de cada um é mostrado na interface.
    "parakeet-v3":  (MOTOR_NVIDIA, "istupakov/parakeet-tdt-0.6b-v3-onnx"),
    "canary-v2":    (MOTOR_NVIDIA, "istupakov/canary-1b-v2-onnx"),
    "parakeet-v2":  (MOTOR_NVIDIA, "istupakov/parakeet-tdt-0.6b-v2-onnx"),
}

#: Nome com que a biblioteca onnx-asr conhece cada modelo NVIDIA.
NOME_ONNX_ASR: dict[str, str] = {
    "parakeet-v3": "nemo-parakeet-tdt-0.6b-v3",
    "canary-v2":   "nemo-canary-1b-v2",
    "parakeet-v2": "nemo-parakeet-tdt-0.6b-v2",
}

#: Idiomas que cada modelo entende, para a interface deixar isso explícito.
#: "*" = praticamente qualquer idioma.
IDIOMAS_DO_MODELO: dict[str, str] = {
    "tiny": "*", "base": "*", "small": "*", "medium": "*",
    "large-v2": "*", "large-v3": "*",
    "parakeet-v3": "europeus",   # 25 idiomas, incluindo português
    "canary-v2": "europeus",     # 25 idiomas, incluindo português
    "parakeet-v2": "en",         # somente inglês
}

MODELOS_DISPONIVEIS = list(CATALOGO_MODELOS)
MODELOS_WHISPER = [n for n, (m, _) in CATALOGO_MODELOS.items() if m == MOTOR_WHISPER]
MODELOS_NVIDIA = [n for n, (m, _) in CATALOGO_MODELOS.items() if m == MOTOR_NVIDIA]


def motor_do_modelo(nome: str) -> str:
    """Qual motor roda esse modelo. Whisper é o padrão para nomes desconhecidos."""
    return CATALOGO_MODELOS.get(nome, (MOTOR_WHISPER, ""))[0]


def repositorio_do_modelo(nome: str) -> str:
    """Repositório no Hugging Face de onde o modelo é baixado."""
    par = CATALOGO_MODELOS.get(nome)
    if par is None:
        raise KeyError(f"Modelo desconhecido: {nome}")
    return par[1]


FORMATOS_DISPONIVEIS = ["txt", "srt", "vtt", "json", "html", "docx", "pdf"]


def formato_disponivel(nome: str) -> bool:
    """Se o formato pode ser gerado nesta build (HTML sempre; DOCX/PDF pedem libs)."""
    if nome in {"txt", "srt", "vtt", "json", "html"}:
        return True
    if nome == "docx":
        try:
            import docx  # noqa: F401
            return True
        except ImportError:
            return False
    if nome == "pdf":
        try:
            import fpdf  # noqa: F401
            return True
        except ImportError:
            return False
    return False


PASTA_ENTRADA_PADRAO = Path("entrada")
PASTA_SAIDA_PADRAO = "saida"
PASTA_DOWNLOADS = PASTA_ENTRADA_PADRAO / "_downloads"

FINALIZADORES_DE_FRASE = (".", "!", "?", "…")
