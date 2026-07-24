"""Configurações e caminhos do aplicativo (pastas de dados, saída, banco)."""

from __future__ import annotations

import os
from pathlib import Path

# Raiz do projeto (a pasta que contém este pacote api/).
RAIZ = Path(__file__).resolve().parent.parent


def _pasta_dados() -> Path:
    """Pasta de dados do app (banco, preferências, logs).

    IMPORTANTE: fica FORA do projeto quando este está dentro do OneDrive. O OneDrive
    sincroniza/bloqueia arquivos em tempo real, o que deixa o SQLite lento e pode
    travar o app. Por isso usamos %LOCALAPPDATA% no Windows (nunca sincronizado)."""
    base = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and base:
        return Path(base) / "Transcritor"
    return Path.home() / ".transcritor"


# Pasta de dados do app (banco de histórico, preferências, logs).
PASTA_DADOS = _pasta_dados()
CAMINHO_BANCO = PASTA_DADOS / "historico.db"

# Pasta padrão de saída das transcrições feitas pela interface.
PASTA_SAIDA_APP = RAIZ / "saida"

# Pasta onde vídeos baixados de URL são guardados.
PASTA_DOWNLOADS_APP = RAIZ / "entrada" / "_downloads"

# Pasta onde arquivos enviados pela interface (upload) são guardados.
PASTA_UPLOADS_APP = RAIZ / "entrada" / "_uploads"

# Build de produção do frontend (gerado por `npm run build`).
PASTA_FRONTEND_DIST = RAIZ / "frontend" / "dist"

# Origem do frontend em modo de desenvolvimento (Vite), liberada no CORS.
ORIGEM_DEV_FRONTEND = "http://localhost:5173"

# Modelo recomendado como padrão quando o usuário ainda não escolheu um.
MODELO_PADRAO_INICIAL = "small"


def garantir_pastas() -> None:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    PASTA_SAIDA_APP.mkdir(parents=True, exist_ok=True)
