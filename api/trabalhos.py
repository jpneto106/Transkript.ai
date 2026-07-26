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
    TranscricaoCancelada,
    atribuir_falantes,
    carregar_modelo_do_motor,
    carregar_pipeline,
    detectar_dispositivo,
    diarizacao_disponivel,
    diarizar_arquivo,
    encontrar_arquivos,
    escrever_saidas,
    montar_blocos,
    rotulos_em_ordem,
    transcrever_com_motor,
)

from . import bd
from .configuracao import PASTA_DOWNLOADS_APP, PASTA_SAIDA_APP

# Estados possíveis de um job (também gravados no banco).
NA_FILA = "na_fila"
BAIXANDO = "baixando"
CARREGANDO_MODELO = "carregando_modelo"
TRANSCREVENDO = "transcrevendo"
DIARIZANDO = "diarizando"
CONCLUIDO = "concluido"
ERRO = "erro"
CANCELADO = "cancelado"

_ROTULOS_STATUS = {
    NA_FILA: "Na fila",
    BAIXANDO: "Baixando arquivo",
    CARREGANDO_MODELO: "Carregando modelo",
    TRANSCREVENDO: "Transcrevendo",
    DIARIZANDO: "Identificando falantes",
    CONCLUIDO: "Concluído",
    ERRO: "Erro",
    CANCELADO: "Cancelado",
}

#: Status em que o job já acabou — não há mais o que cancelar.
STATUS_TERMINAIS = frozenset({CONCLUIDO, ERRO, CANCELADO})


@dataclass
class EstadoJob:
    id: str
    status: str = NA_FILA
    progresso_segundos: float = 0.0
    duracao_total: float | None = None
    mensagem: str = ""
    erro: str | None = None
    versao: int = 0  # incrementa a cada mudança, para o WebSocket detectar novidade
    cancelado: bool = False  # pedido de cancelamento; lido pelo worker entre trechos

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

# Cache do modelo de identificação de vozes, separado do cache do Whisper: os
# dois convivem na GPU e limpar um não pode derrubar o outro.
_pipeline_diarizacao: dict[str, Any] = {}
_pipeline_lock = threading.Lock()


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


def cancelar_job(id_: str) -> str | None:
    """Pede o cancelamento de um job em andamento.

    Devolve o status do job no momento do pedido, ou None se ele não está mais
    em memória. O cancelamento não é imediato: o worker confere a marca entre um
    trecho de áudio e o seguinte, então leva no máximo alguns segundos.
    """
    with _estados_lock:
        estado = _estados.get(id_)
        if estado is None:
            return None
        if estado.status in STATUS_TERMINAIS:
            return estado.status  # já acabou — nada a cancelar
        estado.cancelado = True
        estado.mensagem = "Cancelando…"
        estado.versao += 1
        return estado.status


def _foi_cancelado(id_: str) -> bool:
    with _estados_lock:
        estado = _estados.get(id_)
        return bool(estado and estado.cancelado)


def _parar_se_cancelado(id_: str) -> None:
    """Aborta a etapa atual se o usuário pediu cancelamento."""
    if _foi_cancelado(id_):
        raise TranscricaoCancelada()


def _obter_modelo(nome: str, dispositivo: str, compute_type: str):
    chave = (nome, dispositivo, compute_type)
    with _modelo_lock:
        if chave not in _modelo_cache:
            # Liberar modelos antigos para não acumular VRAM.
            _modelo_cache.clear()
            # O motor certo (Whisper ou NVIDIA) é escolhido pelo nome do modelo.
            _modelo_cache[chave] = carregar_modelo_do_motor(nome, dispositivo, compute_type)
        return _modelo_cache[chave]


def _obter_pipeline_diarizacao(dispositivo: str):
    with _pipeline_lock:
        if dispositivo not in _pipeline_diarizacao:
            _pipeline_diarizacao[dispositivo] = carregar_pipeline(dispositivo)
        return _pipeline_diarizacao[dispositivo]


def _identificar_falantes(
    id_: str,
    resultado,
    arquivo: Path,
    dispositivo: str,
    parametros: dict[str, Any],
) -> None:
    """Roda a diarização e reagrupa os blocos por falante, no lugar.

    Falhar aqui NUNCA derruba o trabalho: a transcrição já está pronta e é o que
    o usuário mais quer. Um problema na identificação de vozes vira aviso.
    """
    _atualizar_estado(id_, status=DIARIZANDO, mensagem=_ROTULOS_STATUS[DIARIZANDO])
    bd.atualizar_transcricao(id_, {"status": DIARIZANDO, "atualizado_em": _agora()})

    def ao_progredir_diarizacao(fracao: float) -> None:
        if resultado.duracao:
            _atualizar_estado(id_, progresso_segundos=min(fracao, 1.0) * resultado.duracao)

    turnos = diarizar_arquivo(
        _obter_pipeline_diarizacao(dispositivo),
        arquivo,
        num_falantes=parametros.get("num_falantes"),
        ao_progredir=ao_progredir_diarizacao,
    )
    _parar_se_cancelado(id_)

    resultado.palavras = atribuir_falantes(resultado.palavras, turnos)
    resultado.falantes = rotulos_em_ordem(resultado.palavras)
    resultado.segmentos = montar_blocos(
        resultado.palavras,
        max_caracteres=parametros["max_caracteres"],
        max_duracao=parametros["max_duracao"],
    )


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

        # O job pode ter sido cancelado enquanto esperava na fila.
        _parar_se_cancelado(id_)

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

        _parar_se_cancelado(id_)

        # 2) Escolher dispositivo e carregar modelo (com cache).
        _atualizar_estado(id_, status=CARREGANDO_MODELO, mensagem=_ROTULOS_STATUS[CARREGANDO_MODELO])
        bd.atualizar_transcricao(id_, {"status": CARREGANDO_MODELO, "atualizado_em": _agora()})

        dispositivo, compute_type = detectar_dispositivo(parametros.get("dispositivo", "auto"))
        modelo = _obter_modelo(parametros["modelo"], dispositivo, compute_type)
        bd.atualizar_transcricao(id_, {"dispositivo": dispositivo, "atualizado_em": _agora()})

        _parar_se_cancelado(id_)

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

        resultado = transcrever_com_motor(
            parametros["modelo"],
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
            cancelado=lambda: _foi_cancelado(id_),
        )

        # 4) Identificar falantes, se pedido e disponível.
        aviso = ""
        if parametros.get("diarizar"):
            _parar_se_cancelado(id_)
            if not diarizacao_disponivel():
                aviso = (
                    "A identificação de falantes não está instalada neste computador; "
                    "a transcrição foi feita sem separar as vozes."
                )
            else:
                try:
                    _identificar_falantes(id_, resultado, arquivo, dispositivo, parametros)
                except TranscricaoCancelada:
                    raise
                except Exception as erro_diarizacao:  # noqa: BLE001
                    # A transcrição já está pronta — vale mais entregá-la com um
                    # aviso do que perder o trabalho todo por causa do extra.
                    aviso = f"Não consegui identificar os falantes: {erro_diarizacao}"

        # 5) Gravar arquivos de saída.
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
            mensagem=aviso or _ROTULOS_STATUS[CONCLUIDO],
            progresso_segundos=resultado.duracao,
            duracao_total=resultado.duracao,
        )

    except TranscricaoCancelada:
        # Interrupção pedida pelo usuário — não é falha, então nada de tela de erro.
        bd.atualizar_transcricao(id_, {"status": CANCELADO, "atualizado_em": _agora()})
        _atualizar_estado(id_, status=CANCELADO, mensagem=_ROTULOS_STATUS[CANCELADO])

    except Exception as erro:  # noqa: BLE001 — queremos reportar qualquer falha ao usuário
        mensagem = str(erro) or "Ocorreu um erro inesperado durante a transcrição."
        bd.atualizar_transcricao(
            id_, {"status": ERRO, "mensagem_erro": mensagem, "atualizado_em": _agora()}
        )
        _atualizar_estado(id_, status=ERRO, erro=mensagem, mensagem=_ROTULOS_STATUS[ERRO])
