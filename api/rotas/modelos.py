"""Rotas de gerenciamento de modelos (listar, baixar, remover)."""

from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException

from nucleo.constantes import MODELOS_DISPONIVEIS

from .. import bd, modelos_cache

router = APIRouter()

# Estado dos downloads em andamento: {nome: "baixando" | "erro" | "concluido"}.
_downloads: dict[str, str] = {}
_downloads_lock = threading.Lock()


@router.get("")
def listar():
    modelo_padrao = bd.obter_config("modelo_padrao")
    modelos = modelos_cache.listar_modelos(modelo_padrao)
    with _downloads_lock:
        for m in modelos:
            if m["nome"] in _downloads:
                m["download_status"] = _downloads[m["nome"]]
    return modelos


def _baixar_em_background(nome: str) -> None:
    try:
        modelos_cache.baixar_modelo(nome)
        with _downloads_lock:
            _downloads[nome] = "concluido"
    except Exception:
        with _downloads_lock:
            _downloads[nome] = "erro"


@router.post("/{nome}/baixar")
def baixar(nome: str):
    if nome not in MODELOS_DISPONIVEIS:
        raise HTTPException(status_code=404, detail="Modelo desconhecido.")
    with _downloads_lock:
        if _downloads.get(nome) == "baixando":
            return {"iniciado": True, "ja_em_andamento": True}
        _downloads[nome] = "baixando"
    threading.Thread(target=_baixar_em_background, args=(nome,), daemon=True).start()
    return {"iniciado": True}


@router.get("/{nome}/progresso")
def progresso(nome: str):
    with _downloads_lock:
        status = _downloads.get(nome)
    return {"nome": nome, "status": status}


@router.delete("/{nome}")
def remover(nome: str):
    if nome not in MODELOS_DISPONIVEIS:
        raise HTTPException(status_code=404, detail="Modelo desconhecido.")
    removido = modelos_cache.remover_modelo(nome)
    if not removido:
        raise HTTPException(status_code=404, detail="Esse modelo não está baixado.")
    with _downloads_lock:
        _downloads.pop(nome, None)
    return {"removido": True}
