"""Rotas de provedores de IA para o resumo por IA (Etapa 7 do plano v4-leve).

Lista o catálogo de provedores e estilos e expõe o endpoint ``POST /resumos``
que de fato chama o provedor escolhido via ``nucleo.resumos.cliente.resumir``.

Erros do provedor (HTTP 5xx, timeout, URL inacessível) viram
``HTTPException(502)`` com a mensagem do ``cliente`` na propriedade
``detail``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from nucleo.resumos.cliente import (
    ConfigResumo,
    provedores_disponiveis,
    resumir as resumir_texto,
)
from nucleo.resumos.provedores import ESTILOS
from ..esquemas import ResumirRequest

router = APIRouter()


@router.get("/provedores")
def listar_provedores():
    """Devolve provedores e estilos para a tela de Resumir."""
    return {
        "provedores": provedores_disponiveis(),
        "estilos": [{"chave": e.chave, "rotulo": e.rotulo, "instrucao": e.instrucao} for e in ESTILOS],
    }


@router.post("/resumos")
def resumir(req: ResumirRequest):
    """Manda o texto para o provedor configurado e devolve o resumo.

    O frontend envia sempre ``texto`` + ``config`` com todos os campos
    preenchidos. Esta rota é síncrona e bloqueia enquanto o provedor
    responde (até o timeout de 180 s definido em ``cliente._executar_*``).
    Para uso normal com um único usuário isso basta.
    """
    config = ConfigResumo(
        chave_provedor=req.config.chave_provedor,
        chave_api=req.config.chave_api,
        modelo=req.config.modelo,
        estilo=req.config.estilo,
        max_tokens=req.config.max_tokens,
    )
    try:
        texto_resumido = resumir_texto(req.texto, config)
    except RuntimeError as erro:
        # Erro do provedor vira 502 Bad Gateway — o frontend mostra a
        # mensagem explicando o que aconteceu (sem precisar decodificar
        # o erro bruto).
        raise HTTPException(status_code=502, detail=str(erro)) from erro
    return {"resumo": texto_resumido}


@router.post("/resumos/testar")
def testar_conexao(req: ResumirRequest):
    """Faz uma chamada curta ao provedor para validar a conexão.

    Envia um prompt mínimo ("Diga OK") e espera resposta. Se o provedor
    responder, considera sucesso. Se falhar (timeout, HTTP 5xx, chave
    inválida), devolve HTTP 502 com a mensagem do erro.
    """
    config = ConfigResumo(
        chave_provedor=req.config.chave_provedor,
        chave_api=req.config.chave_api,
        modelo=req.config.modelo,
        estilo=req.config.estilo,
        max_tokens=10,
    )
    try:
        resumir_texto("Diga OK", config)
    except RuntimeError as erro:
        raise HTTPException(status_code=502, detail=str(erro)) from erro
    return {"status": "ok", "mensagem": "Conexao estabelecida com sucesso."}
