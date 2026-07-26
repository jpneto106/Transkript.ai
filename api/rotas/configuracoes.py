"""Rotas de configuração, opções estáticas e health check."""

from __future__ import annotations

import json

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
    # Modelo padrão continua validado contra o catálogo (Whisper e NVIDIA).
    if req.modelo_padrao is not None:
        if req.modelo_padrao not in MODELOS_DISPONIVEIS:
            raise HTTPException(status_code=400, detail="Modelo desconhecido.")
        bd.definir_config("modelo_padrao", req.modelo_padrao)

    # Demais campos ficam como string no key-value store. Quem serializa
    # (o front) é responsável por usar o formato certo: a lista vira JSON,
    # o booleano vira "1" / "0", etc. Aceitar string mantém o esquema flexível
    # sem inventar uma tabela nova a cada campo.
    campos_string = {
        "idioma_padrao": req.idioma_padrao,
        "preset_blocos": req.preset_blocos,
        "resumo_provedor": req.resumo_provedor,
        "resumo_chave_api": req.resumo_chave_api,
        "resumo_modelo": req.resumo_modelo,
        "resumo_estilo": req.resumo_estilo,
    }
    for chave, valor in campos_string.items():
        if valor is not None:
            bd.definir_config(chave, valor)

    if req.formatos_padrao is not None:
        # Salva como JSON; conferimos que todos são formatos válidos.
        for f in req.formatos_padrao:
            if f not in FORMATOS_DISPONIVEIS:
                raise HTTPException(status_code=400, detail=f"Formato desconhecido: {f!r}")
        bd.definir_config("formatos_padrao", json.dumps(req.formatos_padrao))

    if req.diarizar_por_padrao is not None:
        bd.definir_config("diarizar_por_padrao", "1" if req.diarizar_por_padrao else "0")
    if req.resumo_ativo is not None:
        bd.definir_config("resumo_ativo", "1" if req.resumo_ativo else "0")
    if req.resumo_max_tokens is not None:
        bd.definir_config("resumo_max_tokens", str(req.resumo_max_tokens))

    return bd.obter_todas_configs()
