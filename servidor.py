"""Ponto de entrada do servidor — é este arquivo que o PyInstaller empacota.

Gera o `servidor.exe` que a casca (casca/) sobe como processo filho. Rodando a
partir do código-fonte, equivale a:

    venv\\Scripts\\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8756

⚠️ ORDEM DE IMPORTAÇÃO IMPORTA AQUI ⚠️

`nucleo/` e `api/configuracao.py` calculam todos os seus caminhos (modelos,
banco, saída, frontend) **no momento em que são importados**. Portanto a raiz do
aplicativo precisa estar definida ANTES de qualquer import do projeto — por isso
este arquivo só importa `api` e `nucleo` lá dentro do `main()`, depois de gravar
a variável de ambiente.

Importar `nucleo.caminhos` no topo daqui (mesmo que só para pegar o nome da
variável) já dispararia o cálculo cedo demais e faria o servidor procurar os
modelos e a interface no lugar errado — sem erro nenhum, só um 404 misterioso.
"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path

# Duplicado de propósito: ver o aviso no topo. O valor autoritativo mora em
# nucleo/caminhos.py (VARIAVEL_RAIZ) e os dois precisam continuar iguais —
# existe um teste em testes/test_caminhos.py garantindo isso.
VARIAVEL_RAIZ = "TRANSKRIPT_RAIZ"


def analisar_argumentos(argumentos: list[str] | None = None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        prog="servidor",
        description="Servidor local do Transkript.ai (não acessível pela rede).",
    )
    analisador.add_argument("--host", default="127.0.0.1",
                            help="Endereço de escuta (padrão: 127.0.0.1).")
    analisador.add_argument("--port", type=int, default=8756,
                            help="Porta de escuta (padrão: 8756).")
    analisador.add_argument("--raiz", default=None,
                            help="Pasta do aplicativo (modelos, dados, saída).")
    return analisador.parse_args(argumentos)


def main() -> None:
    # Necessário no Windows quando empacotado: sem isto, qualquer subprocesso
    # criado por bibliotecas relançaria o servidor inteiro em loop.
    multiprocessing.freeze_support()

    argumentos = analisar_argumentos()

    if argumentos.raiz:
        os.environ[VARIAVEL_RAIZ] = str(Path(argumentos.raiz).resolve())

    # --- daqui para baixo já pode importar o projeto ---
    import uvicorn

    from api.configuracao import PASTA_FRONTEND_DIST, RAIZ
    from api.main import app

    # Deixa registrado no log o que foi realmente resolvido. Se algum dia a
    # interface sumir de novo, a resposta está nestas duas linhas.
    print(f"[servidor] raiz do aplicativo: {RAIZ}", flush=True)
    if PASTA_FRONTEND_DIST.is_dir():
        print(f"[servidor] interface: {PASTA_FRONTEND_DIST}", flush=True)
    else:
        print(f"[servidor] AVISO: interface não encontrada em {PASTA_FRONTEND_DIST} "
              f"— a página inicial vai responder 404. Rode 'npm run build' no "
              f"frontend, ou confira o --raiz.", flush=True)

    uvicorn.run(app, host=argumentos.host, port=argumentos.port, log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
