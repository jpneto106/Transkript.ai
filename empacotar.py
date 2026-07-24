"""Monta a pasta completa do aplicativo, pronta para virar instalador.

    venv\\Scripts\\python.exe empacotar.py

Junta as três partes que hoje vivem separadas:

    dist/Transkript.ai/
        Transkript.ai.exe        casca em C# (WebView2), autossuficiente
        app.ico
        servidor/                servidor Python empacotado (PyInstaller)
        frontend/dist/           interface compilada (npm run build)
        ferramentas/ffmpeg/bin/  ffmpeg embutido
        ferramentas/cuda/        DLLs da NVIDIA (aceleração por placa de vídeo)

O que NÃO entra: `modelos/` e `dados/`. Os modelos são baixados no primeiro uso
e os dados nascem com o uso — ambos dentro desta mesma pasta, para que apagar a
pasta (ou desinstalar) leve tudo junto.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "dist" / "Transkript.ai"


def passo(titulo: str) -> None:
    print(f"\n>>> {titulo}", flush=True)


def megabytes(pasta: Path) -> int:
    if not pasta.exists():
        return 0
    total = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file())
    return round(total / 1024 / 1024)


def rodar(comando: list[str], descricao: str) -> None:
    print(f"    {' '.join(comando[:3])} …", flush=True)
    resultado = subprocess.run(comando, cwd=RAIZ)
    if resultado.returncode != 0:
        sys.exit(f"ERRO: {descricao} falhou (código {resultado.returncode}).")


def copiar(origem: Path, destino: Path, descricao: str) -> None:
    if not origem.exists():
        sys.exit(f"ERRO: não encontrei {descricao} em {origem}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True)
    else:
        shutil.copy2(origem, destino)
    print(f"    {descricao}: {megabytes(destino) if origem.is_dir() else 0} MB", flush=True)


def compilar_casca() -> Path:
    passo("Compilando a casca (C#)")
    rodar(
        ["dotnet", "publish", "casca", "-c", "Release", "-r", "win-x64",
         "--self-contained", "true", "-p:PublishSingleFile=false",
         "-p:DebugType=none", "--nologo", "-v", "quiet"],
        "dotnet publish",
    )
    publicado = RAIZ / "casca" / "bin" / "Release" / "net10.0-windows" / "win-x64" / "publish"
    if not (publicado / "Transkript.ai.exe").is_file():
        sys.exit(f"ERRO: não achei Transkript.ai.exe em {publicado}")
    return publicado


def compilar_servidor() -> Path:
    passo("Empacotando o servidor (PyInstaller)")
    rodar([sys.executable, "-m", "PyInstaller", "servidor.spec",
           "--noconfirm", "--log-level", "ERROR"], "pyinstaller")
    pasta = RAIZ / "dist" / "servidor"
    if not (pasta / "servidor.exe").is_file():
        sys.exit(f"ERRO: não achei servidor.exe em {pasta}")
    return pasta


def pasta_nvidia() -> Path:
    """Onde o pip instalou as DLLs de cuBLAS/cuDNN dentro do venv."""
    return Path(sysconfig.get_paths()["purelib"]) / "nvidia"


def main() -> None:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--sem-cuda", action="store_true",
                            help="Não inclui as DLLs da NVIDIA (versão só CPU).")
    analisador.add_argument("--rapido", action="store_true",
                            help="Reaproveita as compilações existentes.")
    argumentos = analisador.parse_args()

    if not (RAIZ / "frontend" / "dist" / "index.html").is_file():
        sys.exit("ERRO: a interface não está compilada.\n"
                 "      Rode:  cd frontend && npm install && npm run build")

    if argumentos.rapido:
        casca = RAIZ / "casca" / "bin" / "Release" / "net10.0-windows" / "win-x64" / "publish"
        servidor = RAIZ / "dist" / "servidor"
        print(">>> Modo rápido: reaproveitando compilações existentes")
    else:
        casca = compilar_casca()
        servidor = compilar_servidor()

    passo(f"Montando {SAIDA}")
    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    SAIDA.mkdir(parents=True)

    copiar(casca, SAIDA, "casca (janela)")
    copiar(RAIZ / "app.ico", SAIDA / "app.ico", "ícone")
    copiar(servidor, SAIDA / "servidor", "servidor")
    copiar(RAIZ / "frontend" / "dist", SAIDA / "frontend" / "dist", "interface")
    copiar(RAIZ / "ferramentas" / "ffmpeg" / "bin",
           SAIDA / "ferramentas" / "ffmpeg" / "bin", "ffmpeg")

    if argumentos.sem_cuda:
        print("    aceleração NVIDIA: pulada (--sem-cuda)")
    else:
        origem_cuda = pasta_nvidia()
        if origem_cuda.is_dir():
            passo("Copiando a aceleração NVIDIA (é grande, demora)")
            for subpasta in sorted(origem_cuda.glob("*/bin")):
                destino = SAIDA / "ferramentas" / "cuda" / subpasta.parent.name / "bin"
                shutil.copytree(subpasta, destino, dirs_exist_ok=True)
            print(f"    ferramentas/cuda: {megabytes(SAIDA / 'ferramentas' / 'cuda')} MB")
        else:
            print(f"    AVISO: {origem_cuda} não existe — saindo sem aceleração NVIDIA.")

    passo("Pronto")
    for nome, caminho in (
        ("casca + runtime", SAIDA),
        ("servidor", SAIDA / "servidor"),
        ("ffmpeg", SAIDA / "ferramentas" / "ffmpeg"),
        ("cuda", SAIDA / "ferramentas" / "cuda"),
    ):
        print(f"    {nome:<18} {megabytes(caminho):>6} MB")
    print(f"\n    Pasta final: {SAIDA}")
    print(f"    Para testar:  \"{SAIDA / 'Transkript.ai.exe'}\"")


if __name__ == "__main__":
    main()
