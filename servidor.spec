# -*- mode: python ; coding: utf-8 -*-
"""Receita do PyInstaller para gerar o `servidor.exe`.

Gera uma PASTA (modo onedir), não um arquivo único. Isso é proposital: o modo
"arquivo único" descompacta o programa inteiro em %TEMP% a cada abertura, o que
deixa resíduo quando o programa fecha mal e ainda atrasa a inicialização.

As DLLs da NVIDIA (cuBLAS/cuDNN, ~2 GB) NÃO entram aqui. Elas vão para
<app>/ferramentas/cuda, seguindo o mesmo padrão do ffmpeg embutido — o que
mantém a compilação rápida e deixa a pasta do programa transparente.

    pyinstaller servidor.spec --noconfirm
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

RAIZ = Path(SPECPATH)  # noqa: F821 — SPECPATH é injetado pelo PyInstaller

datas: list = []
binaries: list = []
hiddenimports: list = []

# Bibliotecas que trazem DLLs, modelos ou dados junto e que o PyInstaller não
# descobre sozinho pela análise estática dos imports.
for pacote in (
    "faster_whisper",    # traz o modelo de detecção de voz (silero VAD)
    "ctranslate2",       # motor do Whisper, cheio de DLLs
    "onnxruntime",
    "onnx_asr",          # motor NVIDIA (Parakeet/Canary em ONNX)
    "av",                # PyAV: leitura de áudio/vídeo
    "tokenizers",
    "yt_dlp",            # download de links
    "huggingface_hub",   # download dos modelos
    # --- identificação de falantes (traz o PyTorch junto: é o que mais pesa) ---
    "pyannote.audio",
    "pyannote.core",
    "pyannote.database",
    "pyannote.pipeline",
    "torch",
    "torchaudio",
    "lightning",
    "lightning_fabric",
    "pytorch_lightning",
    "torchmetrics",
    "speechbrain",
    "asteroid_filterbanks",
    "torch_audiomentations",
    "torch_pitch_shift",
    "pytorch_metric_learning",
    "omegaconf",
    "hydra",
    "sentencepiece",
    "transformers",
):
    try:
        pacote_datas, pacote_binaries, pacote_hidden = collect_all(pacote)
    except Exception:
        # Pacote opcional ausente neste ambiente: seguimos sem ele em vez de
        # abortar a geração inteira.
        continue
    datas += pacote_datas
    binaries += pacote_binaries
    hiddenimports += pacote_hidden

# O uvicorn escolhe protocolos e loops em tempo de execução, por texto — a
# análise estática não enxerga esses imports.
hiddenimports += collect_submodules("uvicorn")

# servidor.py importa a api só dentro da função main() (para poder definir a
# raiz antes), então é preciso apontá-las explicitamente.
hiddenimports += collect_submodules("api")
hiddenimports += collect_submodules("nucleo")

a = Analysis(  # noqa: F821
    ["servidor.py"],
    pathex=[str(RAIZ)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "nvidia",      # vai separado, em ferramentas/cuda
        "tkinter",     # interface é web; nada de Tk
        "matplotlib",
        "PyQt5",
        "PySide6",
    ],
    noarchive=False,
    optimize=0,
)

# O PyTorch guarda, junto das DLLs, bibliotecas de LIGAÇÃO usadas só por quem
# compila código em C++ — nunca carregadas em tempo de execução. Só o dnnl.lib
# tem 2,2 GB. Sem esta limpeza, o instalador carrega ~2,5 GB de peso morto.
_EXTENSOES_DE_COMPILACAO = (".lib", ".a", ".exp", ".pdb")


def _sem_arquivos_de_compilacao(itens):
    return [i for i in itens if not str(i[0]).lower().endswith(_EXTENSOES_DE_COMPILACAO)]


a.datas = _sem_arquivos_de_compilacao(a.datas)
a.binaries = _sem_arquivos_de_compilacao(a.binaries)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="servidor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Aplicativo de console: a casca sobe o processo com a janela escondida e
    # captura a saída para dados/servidor.log. Sem console, perderíamos o log.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="servidor",
)
