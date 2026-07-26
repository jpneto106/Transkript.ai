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
import os
import shutil
import stat
import subprocess
import sys
import sysconfig
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "dist" / "Transkript.ai"


def passo(titulo: str) -> None:
    print(f"\n>>> {titulo}", flush=True)


def remover_arvore(caminho: Path) -> None:
    """Apaga uma pasta inteira, mesmo com arquivos somente-leitura.

    Vários arquivos vindos do site-packages chegam com o atributo de
    somente-leitura, e o `rmtree` do Python falha neles com "Acesso negado".
    Aqui tiramos o atributo e tentamos de novo.
    """
    if not caminho.exists():
        return

    def _forcar(funcao, alvo, _erro):
        try:
            os.chmod(alvo, stat.S_IWRITE)
            funcao(alvo)
        except OSError:
            pass

    shutil.rmtree(caminho, onexc=_forcar)


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


def garantir_ffmpeg() -> Path:
    """Garante que <raiz>/ferramentas/ffmpeg/bin tem ffmpeg.exe e ffprobe.exe.

    Se estiver faltando, baixa o build win64-lgpl-shared do BtbN (com
    conferência de sha256) pelo `instalador/baixar_ffmpeg.py`. O script é
    idempotente: se o cache local já tiver o zip correto, não baixa de novo.
    """
    caminho_bin = RAIZ / "ferramentas" / "ffmpeg" / "bin"
    if (caminho_bin / "ffmpeg.exe").is_file() and (caminho_bin / "ffprobe.exe").is_file():
        return caminho_bin
    print("    ffmpeg ausente em", caminho_bin, "— baixando build LGPL do BtbN…")
    baixar = RAIZ / "instalador" / "baixar_ffmpeg.py"
    if not baixar.is_file():
        sys.exit(f"ERRO: não achei o baixador de ffmpeg em {baixar}")
    rodar([sys.executable, str(baixar)], "baixar_ffmpeg.py")
    if not (caminho_bin / "ffmpeg.exe").is_file():
        sys.exit("ERRO: o ffmpeg.exe não apareceu após o download.")
    return caminho_bin


def pasta_nvidia() -> Path:
    """Onde o pip instalou as DLLs de cuBLAS/cuDNN dentro do venv."""
    return Path(sysconfig.get_paths()["purelib"]) / "nvidia"


#: Modelo de identificação de vozes: só 32 MB, então vai junto do programa.
#: Assim o usuário tem o recurso pronto, sem baixar nada e sem nunca precisar
#: de conta no Hugging Face (o repositório original é fechado por formulário).
PASTA_MODELO_VOZES = "models--pyannote--speaker-diarization-community-1"


def copiar_modelo_de_vozes(destino: Path) -> None:
    origem = RAIZ / "modelos" / "hub" / PASTA_MODELO_VOZES
    if not origem.is_dir():
        print(f"    AVISO: modelo de vozes não encontrado em {origem}")
        print("           a diarização ficará indisponível no programa instalado.")
        return
    alvo = destino / "modelos" / "hub" / PASTA_MODELO_VOZES
    shutil.copytree(origem, alvo, dirs_exist_ok=True)
    print(f"    modelo de vozes: {megabytes(alvo)} MB")


def main() -> None:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--sem-cuda", action="store_true",
                            help="Não inclui as DLLs da NVIDIA (versão só CPU).")
    analisador.add_argument("--rapido", action="store_true",
                            help="Reaproveita as compilações existentes.")
    analisador.add_argument("--bootstrap", action="store_true",
                            help="Produz o instalador bootstrap (só casca + launcher; "
                                 "o resto baixa na primeira execução). É o par leve do "
                                 "instalador completo, sem o conteúdo embutido.")
    argumentos = analisador.parse_args()

    if not (RAIZ / "frontend" / "dist" / "index.html").is_file():
        sys.exit("ERRO: a interface não está compilada.\n"
                 "      Rode:  cd frontend && npm install && npm run build")

    caminho_ffmpeg = garantir_ffmpeg()

    if argumentos.rapido:
        casca = RAIZ / "casca" / "bin" / "Release" / "net10.0-windows" / "win-x64" / "publish"
        servidor = RAIZ / "dist" / "servidor"
        print(">>> Modo rápido: reaproveitando compilações existentes")
    else:
        casca = compilar_casca()
        servidor = compilar_servidor()

    passo(f"Montando {SAIDA}")
    remover_arvore(SAIDA)
    SAIDA.mkdir(parents=True)

    copiar(casca, SAIDA, "casca (janela)")
    copiar(RAIZ / "app.ico", SAIDA / "app.ico", "ícone")

    if argumentos.bootstrap:
        # Modo bootstrap: só casca + launcher. O resto baixa do GitHub Releases
        # na primeira execução, via `instalador/baixar_componentes.py` (invocado
        # pelo launcher integrado na casca — Etapa 6).
        copiar(RAIZ / "instalador" / "baixar_componentes.py",
               SAIDA / "instalador" / "baixar_componentes.py",
               "buscador de componentes (primeira execução)")
        copiar(RAIZ / "instalador" / "ASSETS.md",
               SAIDA / "instalador" / "ASSETS.md",
               "convencao dos assets")
    else:
        copiar(servidor, SAIDA / "servidor", "servidor")
        copiar(RAIZ / "frontend" / "dist", SAIDA / "frontend" / "dist", "interface")
        copiar(RAIZ / "ferramentas" / "ffmpeg" / "bin",
               SAIDA / "ferramentas" / "ffmpeg" / "bin", "ffmpeg")
        copiar_modelo_de_vozes(SAIDA)

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
    if argumentos.bootstrap:
        print(f"    MODO BOOTSTRAP: instalador fino. O restante baixa via baixar_componentes.py")
    for nome, caminho in (
        ("casca + runtime", SAIDA),
        ("servidor", SAIDA / "servidor"),
        ("ffmpeg", SAIDA / "ferramentas" / "ffmpeg"),
        ("cuda", SAIDA / "ferramentas" / "cuda"),
    ):
        if caminho.exists() or caminho.is_dir():
            print(f"    {nome:<18} {megabytes(caminho):>6} MB")
    print(f"\n    Pasta final: {SAIDA}")
    print(f"    Para testar:  \"{SAIDA / 'Transkript.ai.exe'}\"")


if __name__ == "__main__":
    main()
