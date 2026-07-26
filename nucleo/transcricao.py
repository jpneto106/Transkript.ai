"""Carregamento do modelo Whisper e transcrição de um arquivo, com progresso agnóstico de UI."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .blocos import extrair_palavras, montar_blocos
from .formatacao import ResultadoTranscricao


@dataclass
class EventoProgresso:
    """Evento de progresso emitido durante a transcrição de um arquivo.

    - arquivo: qual arquivo está sendo transcrito;
    - segundos_concluidos: quantos segundos de áudio já foram processados;
    - duracao_total: duração total do áudio (None se desconhecida).
    """
    arquivo: Path
    segundos_concluidos: float
    duracao_total: float | None


CallbackProgresso = Callable[[EventoProgresso], None]

#: Consultado entre um trecho e outro; devolvendo True, a transcrição é abortada.
VerificadorCancelamento = Callable[[], bool]


class TranscricaoCancelada(Exception):
    """Levantada quando o usuário cancela a transcrição em andamento.

    É uma interrupção pedida, não uma falha: quem chama deve tratá-la como
    cancelamento (e não mostrar tela de erro ao usuário).
    """


def carregar_modelo(nome: str, dispositivo: str, compute_type: str):
    """Carrega um WhisperModel. Isolado numa função para que CLI e API possam
    cachear/reaproveitar o modelo carregado sem duplicar o import."""
    from faster_whisper import WhisperModel

    return WhisperModel(nome, device=dispositivo, compute_type=compute_type)


def transcrever_arquivo(
    modelo,
    arquivo: Path,
    *,
    idioma: str | None,
    tarefa: str,
    beam_size: int,
    vad_filter: bool,
    max_caracteres: int,
    max_duracao: float,
    initial_prompt: str | None = None,
    ao_progredir: CallbackProgresso | None = None,
    cancelado: VerificadorCancelamento | None = None,
) -> ResultadoTranscricao:
    segmentos_gerados, info = modelo.transcribe(
        str(arquivo),
        language=idioma,
        task=tarefa,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=True,
        initial_prompt=initial_prompt,
    )

    duracao = info.duration

    resultado = ResultadoTranscricao(
        arquivo=arquivo,
        idioma=info.language,
        probabilidade_idioma=info.language_probability,
        duracao=duracao,
    )

    def _emitir(concluido: float) -> None:
        if ao_progredir is not None:
            ao_progredir(EventoProgresso(arquivo, concluido, duracao))

    segmentos_brutos = []
    inicio_processamento = time.perf_counter()
    # O faster-whisper devolve um gerador preguiçoso: o trabalho pesado acontece
    # a cada iteração. Por isso conferir o cancelamento aqui interrompe de fato
    # o processamento, e não só a coleta dos resultados.
    for seg in segmentos_gerados:
        if cancelado is not None and cancelado():
            raise TranscricaoCancelada()
        segmentos_brutos.append(seg)
        _emitir(min(seg.end, duracao) if duracao else seg.end)
    if duracao:
        _emitir(duracao)
    resultado.tempo_processamento = time.perf_counter() - inicio_processamento

    palavras = extrair_palavras(segmentos_brutos)
    # Guardadas para a diarização poder remontar os blocos depois, sem precisar
    # transcrever o áudio outra vez.
    resultado.palavras = palavras
    resultado.segmentos = montar_blocos(palavras, max_caracteres=max_caracteres, max_duracao=max_duracao)

    return resultado
