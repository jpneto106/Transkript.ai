"""Configurações e caminhos do aplicativo (pastas de dados, saída, banco)."""

from __future__ import annotations

from pathlib import Path

from nucleo.caminhos import RAIZ_APP

# Raiz do aplicativo. Vem de nucleo/caminhos.py para que o programa empacotado
# guarde modelos, banco e saídas na pasta visível do app — e não escondidos
# dentro do executável, onde o desinstalador não os encontraria.
RAIZ = RAIZ_APP


def _pasta_dados() -> Path:
    """Pasta de dados do app (banco, preferências, logs).

    App portátil: fica DENTRO da pasta do programa (<app>/dados), para que apagar a
    pasta remova tudo. A recomendação é manter o programa FORA do OneDrive, para o
    OneDrive não sincronizar/bloquear o banco SQLite em tempo real."""
    return RAIZ / "dados"


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
