"""Configurações e caminhos do aplicativo (pastas de dados, saída, banco)."""

from __future__ import annotations

from pathlib import Path

# Raiz do projeto (a pasta que contém este pacote api/).
RAIZ = Path(__file__).resolve().parent.parent

# Pasta de dados do app (banco de histórico, preferências). Fora do git.
PASTA_DADOS = RAIZ / "dados_app"
CAMINHO_BANCO = PASTA_DADOS / "historico.db"

# Pasta padrão de saída das transcrições feitas pela interface.
PASTA_SAIDA_APP = RAIZ / "saida"

# Pasta onde vídeos baixados de URL são guardados.
PASTA_DOWNLOADS_APP = RAIZ / "entrada" / "_downloads"

# Build de produção do frontend (gerado por `npm run build`).
PASTA_FRONTEND_DIST = RAIZ / "frontend" / "dist"

# Origem do frontend em modo de desenvolvimento (Vite), liberada no CORS.
ORIGEM_DEV_FRONTEND = "http://localhost:5173"

# Modelo recomendado como padrão quando o usuário ainda não escolheu um.
MODELO_PADRAO_INICIAL = "small"


def garantir_pastas() -> None:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    PASTA_SAIDA_APP.mkdir(parents=True, exist_ok=True)
