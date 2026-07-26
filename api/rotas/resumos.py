"""Rotas de provedores de IA para o resumo por IA (Etapa 7 do plano v4-leve).

Apenas lista os provedores suportados e os estilos de resumo. O endpoint
``POST /resumos`` que de fato chama o provedor escolhido vai entrar em outra
rota; este arquivo só expõe o catálogo para o frontend.
"""

from __future__ import annotations

from fastapi import APIRouter

from nucleo.resumos.cliente import provedores_disponiveis
from nucleo.resumos.provedores import ESTILOS

router = APIRouter()


@router.get("/provedores")
def listar_provedores():
    """Devolve provedores e estilos para a tela de Configurações."""
    return {
        "provedores": provedores_disponiveis(),
        "estilos": [{"chave": e.chave, "rotulo": e.rotulo} for e in ESTILOS],
    }


@router.post("/resumos")
def resumir(req: dict):
    """Stub — a implementação completa entra na Etapa 7.4.1.

    Por enquanto devolve uma mensagem pedindo para usar o ``transcrever.py`` /
    API Python diretamente, mantendo o frontend funcional. Quando o stub
    for substituído, o payload esperado é::

        {
          "texto": "<texto a resumir>",
          "chave_provedor": "ollama",
          "chave_api": "",
          "modelo": "",
          "estilo": "curto",
          "max_tokens": 1024
        }

    A resposta é ``{"resumo": "..."}`` ou um erro HTTP 4xx/5xx.
    """
    return {
        "resumo": "",
        "aviso": "Endpoint ainda não implementado. Use Configurações para ativar/desativar.",
    }
