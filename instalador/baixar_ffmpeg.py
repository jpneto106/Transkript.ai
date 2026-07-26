"""Baixa o build LGPL do ffmpeg usado pelo Transkript.ai v4.

Usado durante o empacotamento (`empacotar.py` chama este script se o ffmpeg ainda
não estiver em `ferramentas/ffmpeg/bin/`). É idempotente: se o executável já
existir, não baixa de novo.

    python instalador/baixar_ffmpeg.py [destino]

Padrão do destino: <raiz do projeto>/ferramentas/ffmpeg/bin/

A origem, a versão e o sha256 esperados estão fixados no início deste arquivo —
são as três informações que precisam casar com o hash publicado em
https://github.com/BtbN/FFmpeg-Builds/releases/latest (asset
`ffmpeg-master-latest-win64-lgpl-shared.zip`).
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# === Origem fixa do ffmpeg (build win64-lgpl-shared, BtbN / FFmpeg-Builds) ===
# Atualizar a versão requer conferir os bytes do arquivo publicado; o sha256
# abaixo é conferido no ato do download e o download é abortado se não bater.
FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-lgpl-shared.zip"
)
FFMPEG_SHA256 = "326b627e9e7267fd2d987f3455b1d0f5a0a5e116841e27db707ec9a04d6b4873"

NOME_ARQUIVO = "ffmpeg.exe"
NOME_FFPROBE = "ffprobe.exe"


def raiz_destino(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    return Path(__file__).resolve().parent.parent / "ferramentas" / "ffmpeg" / "bin"


def ja_esta_pronto(destino: Path) -> bool:
    return (destino / NOME_ARQUIVO).is_file() and (destino / NOME_FFPROBE).is_file()


def baixar_com_progresso(url: str, destino: Path) -> None:
    """Faz o download mostrando o progresso em MB downloaded / total."""
    print(f"  baixando {url}")
    with urllib.request.urlopen(url, timeout=300) as resposta:
        tamanho_total = int(resposta.headers.get("Content-Length", "0"))
        lidos = 0
        bloco = 1024 * 64
        with open(destino, "wb") as saida:
            while True:
                pedaco = resposta.read(bloco)
                if not pedaco:
                    break
                saida.write(pedaco)
                lidos += len(pedaco)
                if tamanho_total:
                    mb = lidos / 1024 / 1024
                    total_mb = tamanho_total / 1024 / 1024
                    pct = 100 * lidos / tamanho_total
                    print(f"\r    {mb:6.1f} / {total_mb:6.1f} MB  ({pct:5.1f}%)", end="")
        if tamanho_total:
            print()


def conferir_sha256(arquivo: Path, esperado: str) -> None:
    print("  conferindo sha256...", end=" ", flush=True)
    sha = hashlib.sha256()
    with open(arquivo, "rb") as f:
        for pedaco in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(pedaco)
    calculado = sha.hexdigest()
    if calculado.lower() != esperado.lower():
        print("FALHOU")
        print(f"    esperado : {esperado}")
        print(f"    calculado: {calculado}")
        sys.exit("ERRO: sha256 do ffmpeg não bateu. Remova o .zip baixado e tente de novo.")
    print("ok")


def extrair_para(zip_path: Path, destino: Path) -> None:
    """Extrai só `bin/ffmpeg.exe` e `bin/ffprobe.exe` (e as DLLs do mesmo nível)."""
    print(f"  extraindo binários para {destino}")
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        binarios = [
            nome for nome in zf.namelist()
            if nome.startswith("ffmpeg-") and "/bin/" in nome and "/" not in nome.split("/bin/", 1)[1]
        ]
        for nome in binarios:
            conteudo = zf.read(nome)
            alvo = destino / Path(nome).name
            with open(alvo, "wb") as saida:
                saida.write(conteudo)


def main(argv: list[str]) -> int:
    destino = raiz_destino(argv[1] if len(argv) > 1 else None)
    print(f"Destino: {destino}")

    if ja_esta_pronto(destino):
        print(f"  {NOME_ARQUIVO} e {NOME_FFPROBE} já existem. Nada a fazer.")
        return 0

    cache = Path(__file__).resolve().parent / "_cache"
    cache.mkdir(exist_ok=True)
    zip_destino = cache / "ffmpeg-win64-lgpl-shared.zip"

    if not zip_destino.is_file():
        baixar_com_progresso(FFMPEG_URL, zip_destino)
    else:
        print(f"  usando cache: {zip_destino}")

    conferir_sha256(zip_destino, FFMPEG_SHA256)
    extrair_para(zip_destino, destino)

    for exe in (NOME_ARQUIVO, NOME_FFPROBE):
        if not (destino / exe).is_file():
            sys.exit(f"ERRO: {exe} não apareceu em {destino} após extração.")
        print(f"    {exe}: {(destino / exe).stat().st_size / 1024 / 1024:.1f} MB")
    print(f"OK: ffmpeg LGPL pronto em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
