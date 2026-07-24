"""Rotas de dicionários de termos (vocabulário para melhorar a transcrição)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from .. import bd
from ..esquemas import DicionarioRequest

router = APIRouter()


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
def listar():
    return bd.listar_dicionarios()


@router.post("")
def criar(req: DicionarioRequest):
    id_ = uuid.uuid4().hex
    agora = _agora()
    bd.inserir_dicionario(
        {
            "id": id_,
            "nome": req.nome,
            "descricao": req.descricao,
            "termos": [t.strip() for t in req.termos if t.strip()],
            "criado_em": agora,
            "atualizado_em": agora,
        }
    )
    return bd.obter_dicionario(id_)


@router.put("/{id_}")
def atualizar(id_: str, req: DicionarioRequest):
    if bd.obter_dicionario(id_) is None:
        raise HTTPException(status_code=404, detail="Dicionário não encontrado.")
    bd.atualizar_dicionario(
        id_,
        {
            "nome": req.nome,
            "descricao": req.descricao,
            "termos": [t.strip() for t in req.termos if t.strip()],
            "atualizado_em": _agora(),
        },
    )
    return bd.obter_dicionario(id_)


@router.delete("/{id_}")
def remover(id_: str):
    if bd.obter_dicionario(id_) is None:
        raise HTTPException(status_code=404, detail="Dicionário não encontrado.")
    bd.remover_dicionario(id_)
    return {"removido": True}
