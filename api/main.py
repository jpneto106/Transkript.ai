"""Fábrica do app FastAPI: registra rotas, CORS e serve o frontend buildado."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import bd
from .configuracao import ORIGEM_DEV_FRONTEND, PASTA_FRONTEND_DIST, garantir_pastas
from .rotas import configuracoes, dicionarios, modelos, resumos, transcricoes


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    garantir_pastas()
    bd.criar_tabelas()
    yield


def criar_app() -> FastAPI:
    app = FastAPI(title="Transcritor API", version="1.0", lifespan=ciclo_de_vida)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGEM_DEV_FRONTEND],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rotas de API (registradas ANTES do mount estático, senão o "/" engole tudo).
    app.include_router(transcricoes.router, prefix="/api/transcricoes", tags=["transcricoes"])
    app.include_router(modelos.router, prefix="/api/modelos", tags=["modelos"])
    app.include_router(dicionarios.router, prefix="/api/dicionarios", tags=["dicionarios"])
    app.include_router(configuracoes.router, prefix="/api", tags=["config"])
    app.include_router(resumos.router, prefix="/api", tags=["resumos"])

    # Frontend de produção (só existe depois de `npm run build`).
    if PASTA_FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=PASTA_FRONTEND_DIST, html=True), name="frontend")

    return app


# Instância para `uvicorn api.main:app` (sem --factory).
app = criar_app()
