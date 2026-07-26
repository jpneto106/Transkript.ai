"""Rotas de configuração, opções estáticas e health check."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from nucleo import diarizacao_disponivel, motores_disponiveis
from nucleo.constantes import FORMATOS_DISPONIVEIS, MODELOS_DISPONIVEIS

from .. import bd
from ..configuracao import PASTA_SAIDA_APP
from ..esquemas import AtualizarConfigRequest

router = APIRouter()


@router.get("/saude")
def saude():
    return {"status": "ok"}


@router.get("/opcoes")
def opcoes():
    return {
        "modelos": MODELOS_DISPONIVEIS,
        "formatos": FORMATOS_DISPONIVEIS,
        "pasta_saida": str(PASTA_SAIDA_APP),
        # A interface usa isto para habilitar (ou explicar a ausência da) opção
        # de identificar falantes, em vez de deixar o usuário marcar algo que
        # não vai funcionar.
        "diarizacao_disponivel": diarizacao_disponivel(),
        # Quais motores de transcrição este computador consegue rodar. A tela de
        # Modelos usa isto para avisar quando um motor não está instalado, em vez
        # de deixar o usuário baixar um modelo que não vai funcionar.
        "motores": motores_disponiveis(),
    }


@router.get("/config")
def obter_config():
    return bd.obter_todas_configs()


@router.put("/config")
def atualizar_config(req: AtualizarConfigRequest):
    if req.modelo_padrao is not None:
        if req.modelo_padrao not in MODELOS_DISPONIVEIS:
            raise HTTPException(status_code=400, detail="Modelo desconhecido.")
        bd.definir_config("modelo_padrao", req.modelo_padrao)
    return bd.obter_todas_configs()
