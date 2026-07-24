"""Fila de transcrição (1 worker), estado em memória e cache do modelo carregado."""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nucleo import (
    EventoProgresso,
    carregar_modelo,
    detectar_dispositivo,
    encontrar_arquivos,
    escrever_saidas,
    transcrever_arquivo,
)

from . import bd
from .configuracao import PASTA_DOWNLOADS_APP, PASTA_SAIDA_APP

# Estados possíveis de um job (também gravados no banco).
NA_FILA = "na_fila"
BAIXANDO = "baixando"
CARREGANDO_MODELO = "carregando_modelo"
TRANSCREVENDO = "transcrevendo"
CONCLUIDO = "concluido"
ERRO = "erro"

_ROTULOS_STATUS = {
    NA_FILA: "Na fila",
    BAIXANDO: "Baixando arquivo",
    CARREGANDO_MODELO: "Carregando modelo",
    TRANSCREVENDO: "Transcrevendo",
    CONCLUIDO: "Concluído",
    ERRO: "Erro",
}


@dataclass
class EstadoJob:
    id: str
    status: str = NA_FILA
    progresso_segundos: float = 0.0
    duracao_total: float | None = None
    mensagem: str = ""
    erro: str | None = None
    versao: int = 0  # incrementa a cada mudança, para o WebSocket detectar novidade

    def snapshot(self) -> dict[str, Any]:
        percentual = None
        if self.duracao_total:
            percentual = min(100.0, round(self.progresso_segundos / self.duracao_total * 100, 1))
        return {
            "id": self.id,
            "status": self.status,
            "rotulo_status": _ROTULOS_STATUS.get(self.status, self.status),
            "progresso_segundos": round(self.progresso_segundos, 1),
            "duracao_total": round(self.duracao_total, 1) if self.duracao_total else None,
            "percentual": percentual,
            "mensagem": self.mensagem,
            "erro": self.erro,
            "versao": self.versao,
        }


_estados: dict[str, EstadoJob] = {}
_estados_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="transcricao")

# Cache do último modelo carregado, chaveado por (nome, dispositivo, compute_type).
_modelo_cache: dict[tuple[str, str, str], Any] = {}
_modelo_lock = threading.Lock()


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atualizar_estado(id_: str, **campos) -> None:
    with _estados_lock:
        estado = _estados.get(id_)
        if estado is None:
            return
        for k, v in campos.items():
            setattr(estado, k, v)
        estado.versao += 1


def obter_estado(id_: str) -> dict[str, Any] | None:
    with _estados_lock:
        estado = _estados.get(id_)
        return estado.snapshot() if estado else None


def _obter_modelo(nome: str, dispositivo: str, compute_type: str):
    chave = (nome, dispositivo, compute_type)
    with _modelo_lock:
        if chave not in _modelo_cache:
            # Liberar modelos antigos para não acumular VRAM.
            _modelo_cache.clear()
            _modelo_cache[chave] = carregar_modelo(nome, dispositivo, compute_type)
        return _modelo_cache[chave]


def criar_job(parametros: dict[str, Any]) -> str:
    """Registra um novo job (no banco e em memória) e o enfileira. Retorna o id."""
    id_ = uuid.uuid4().hex
    agora = _agora()

    registro = {
        "id": id_,
        "criado_em": agora,
        "atualizado_em": agora,
        "entrada_original": parametros["entrada"],
        "arquivo_local": None,
        "nome_arquivo": None,
        "modelo": parametros["modelo"],
        "idioma_solicitado": parametros.get("idioma"),
        "idioma_detectado": None,
        "probabilidade_idioma": None,
        "tarefa": parametros.get("tarefa", "transcribe"),
        "dispositivo": parametros.get("dispositivo", "auto"),
        "formatos": parametros["formatos"],
        "max_caracteres": parametros["max_caracteres"],
        "max_duracao": parametros["max_duracao"],
        "pasta_saida": str(PASTA_SAIDA_APP),
        "duracao_audio": None,
        "tempo_processamento": None,
        "status": NA_FILA,
        "progresso_segundos": 0,
        "mensagem_erro": None,
        "arquivos_gerados": [],
    }
    bd.inserir_transcricao(registro)

    with _estados_lock:
        _estados[id_] = EstadoJob(id=id_, status=NA_FILA, mensagem=_ROTULOS_STATUS[NA_FILA])

    _executor.submit(_processar_job, id_, parametros)
    return id_


def _processar_job(id_: str, parametros: dict[str, Any]) -> None:
    try:
        entrada = parametros["entrada"]

        # 1) Resolver a entrada (baixar se for URL).
        _atualizar_estado(id_, status=BAIXANDO, mensagem=_ROTULOS_STATUS[BAIXANDO])
        bd.atualizar_transcricao(id_, {"status": BAIXANDO, "atualizado_em": _agora()})

        arquivos = encontrar_arquivos([entrada], PASTA_DOWNLOADS_APP)
        if not arquivos:
            raise ValueError(
                "Não encontrei nenhum arquivo de áudio/vídeo válido nessa entrada. "
                "Verifique se o caminho ou o link está correto."
            )
        arquivo = arquivos[0]
        bd.atualizar_transcricao(
            id_,
            {"arquivo_local": str(arquivo), "nome_arquivo": arquivo.name, "atualizado_em": _agora()},
        )

        # 2) Escolher dispositivo e carregar modelo (com cache).
        _atualizar_estado(id_, status=CARREGANDO_MODELO, mensagem=_ROTULOS_STATUS[CARREGANDO_MODELO])
        bd.atualizar_transcricao(id_, {"status": CARREGANDO_MODELO, "atualizado_em": _agora()})

        dispositivo, compute_type = detectar_dispositivo(parametros.get("dispositivo", "auto"))
        modelo = _obter_modelo(parametros["modelo"], dispositivo, compute_type)
        bd.atualizar_transcricao(id_, {"dispositivo": dispositivo, "atualizado_em": _agora()})

        # 3) Transcrever, emitindo progresso.
        _atualizar_estado(id_, status=TRANSCREVENDO, mensagem=_ROTULOS_STATUS[TRANSCREVENDO])
        bd.atualizar_transcricao(id_, {"status": TRANSCREVENDO, "atualizado_em": _agora()})

        # Dicionário de termos -> initial_prompt (enviesa o modelo a reconhecer os termos).
        initial_prompt = None
        dic_id = parametros.get("dicionario_id")
        if dic_id:
            dic = bd.obter_dicionario(dic_id)
            if dic and dic.get("termos"):
                initial_prompt = ", ".join(dic["termos"])

        def ao_progredir(evento: EventoProgresso) -> None:
            _atualizar_estado(
                id_,
                progresso_segundos=evento.segundos_concluidos,
                duracao_total=evento.duracao_total,
            )

        resultado = transcrever_arquivo(
            modelo,
            arquivo,
            idioma=parametros.get("idioma"),
            tarefa=parametros.get("tarefa", "transcribe"),
            beam_size=parametros.get("beam_size", 5),
            vad_filter=parametros.get("vad_filter", True),
            max_caracteres=parametros["max_caracteres"],
            max_duracao=parametros["max_duracao"],
            initial_prompt=initial_prompt,
            ao_progredir=ao_progredir,
        )

        # 4) Gravar arquivos de saída.
        gerados = escrever_saidas(resultado, PASTA_SAIDA_APP, parametros["formatos"])

        bd.atualizar_transcricao(
            id_,
            {
                "status": CONCLUIDO,
                "idioma_detectado": resultado.idioma,
                "probabilidade_idioma": resultado.probabilidade_idioma,
                "duracao_audio": resultado.duracao,
                "tempo_processamento": resultado.tempo_processamento,
                "progresso_segundos": resultado.duracao,
                "arquivos_gerados": [str(g) for g in gerados],
                "atualizado_em": _agora(),
            },
        )
        _atualizar_estado(
            id_,
            status=CONCLUIDO,
            mensagem=_ROTULOS_STATUS[CONCLUIDO],
            progresso_segundos=resultado.duracao,
            duracao_total=resultado.duracao,
        )

    except Exception as erro:  # noqa: BLE001 — queremos reportar qualquer falha ao usuário
        mensagem = str(erro) or "Ocorreu um erro inesperado durante a transcrição."
        bd.atualizar_transcricao(
            id_, {"status": ERRO, "mensagem_erro": mensagem, "atualizado_em": _agora()}
        )
        _atualizar_estado(id_, status=ERRO, erro=mensagem, mensagem=_ROTULOS_STATUS[ERRO])
