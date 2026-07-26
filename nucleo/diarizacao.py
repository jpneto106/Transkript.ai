"""Identificação de falantes (diarização) com o WhisperX/pyannote.

O Whisper sabe O QUE foi dito e QUANDO; não sabe QUEM falou. Este módulo roda um
segundo modelo, que devolve os turnos de fala ("da 0:00 à 0:42 foi a voz A"), e
cruza esses turnos com as palavras já transcritas.

Duas decisões de projeto importantes:

1. **O usuário final nunca precisa de conta no Hugging Face.** O modelo (32 MB)
   é baixado uma única vez pelo autor e vai junto do programa, em
   <app>/modelos. Para garantir que nenhuma instalação tente falar com a
   internet — e falhe por falta de token —, o modelo é carregado em modo
   estritamente local.

2. **A dependência é opcional.** O WhisperX traz o PyTorch junto (~2,5 GB). Os
   imports ficam dentro das funções, e `diarizacao_disponivel()` permite ao
   aplicativo simplesmente não oferecer o recurso quando ele não está instalado,
   em vez de quebrar.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .caminhos import RAIZ_APP
from .formatacao import Palavra

#: Repositório usado pelo WhisperX 3.8.x. Fixado aqui para o download do autor e
#: a checagem de disponibilidade falarem exatamente do mesmo modelo.
REPO_DIARIZACAO = "pyannote/speaker-diarization-community-1"

#: Progresso de 0.0 a 1.0 durante a diarização.
CallbackProgressoDiarizacao = Callable[[float], None]


@dataclass
class TurnoFalante:
    """Um trecho contínuo em que uma única voz fala."""
    inicio: float
    fim: float
    falante: str


def _pasta_modelos() -> Path:
    return RAIZ_APP / "modelos"


def pasta_do_modelo() -> Path:
    return _pasta_modelos() / "hub" / ("models--" + REPO_DIARIZACAO.replace("/", "--"))


def modelo_baixado() -> bool:
    """True se o modelo de vozes já está na pasta do programa.

    Exige o config.yaml e os dois pesos (segmentação e embedding) — só a pasta
    existir não basta, porque um download interrompido deixa a pasta pela metade.
    """
    pasta = pasta_do_modelo()
    if not pasta.is_dir():
        return False
    tem_config = any(pasta.rglob("config.yaml"))
    pesos = {p.parent.name for p in pasta.rglob("pytorch_model.bin")}
    return tem_config and {"segmentation", "embedding"} <= pesos


def biblioteca_instalada() -> bool:
    """True se o WhisperX (e o PyTorch junto) está instalado neste ambiente."""
    from importlib.util import find_spec

    try:
        return find_spec("whisperx") is not None
    except (ImportError, ValueError):
        return False


def diarizacao_disponivel() -> bool:
    """Só oferecemos o recurso quando as duas peças existem."""
    return biblioteca_instalada() and modelo_baixado()


@contextmanager
def _somente_arquivos_locais():
    """Impede qualquer ida à internet ao carregar o modelo.

    Sem isto, a biblioteca tentaria consultar o Hugging Face; como o repositório
    é fechado, uma instalação sem token receberia 403 mesmo tendo o modelo em
    disco. Em modo local o token deixa de ser necessário — que é exatamente o
    que queremos para quem instala o programa.
    """
    anteriores = {k: os.environ.get(k) for k in ("HF_HUB_OFFLINE", "HF_HOME", "HF_HUB_DISABLE_SYMLINKS")}
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ.setdefault("HF_HOME", str(_pasta_modelos()))
    os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
    try:
        yield
    finally:
        for chave, valor in anteriores.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor


def carregar_pipeline(dispositivo: str):
    """Carrega o modelo de identificação de vozes. Reutilize — é caro."""
    with _somente_arquivos_locais():
        from whisperx.diarize import DiarizationPipeline

        return DiarizationPipeline(device=dispositivo, cache_dir=str(_pasta_modelos()))


def diarizar_arquivo(
    pipeline,
    arquivo: Path,
    *,
    num_falantes: int | None = None,
    ao_progredir: CallbackProgressoDiarizacao | None = None,
) -> list[TurnoFalante]:
    """Devolve os turnos de fala do arquivo, já com rótulos canônicos.

    `num_falantes` força a quantidade quando o usuário sabe (mais preciso);
    None deixa o modelo descobrir sozinho.
    """
    with _somente_arquivos_locais():
        resultado = pipeline(
            str(arquivo),
            num_speakers=num_falantes,
            progress_callback=ao_progredir,
        )

    # A pipeline devolve um DataFrame (ou uma tupla, quando se pede embeddings).
    tabela = resultado[0] if isinstance(resultado, tuple) else resultado

    turnos: list[TurnoFalante] = []
    for linha in tabela.itertuples():
        turnos.append(
            TurnoFalante(
                inicio=float(linha.start),
                fim=float(linha.end),
                falante=str(linha.speaker),
            )
        )
    turnos.sort(key=lambda t: (t.inicio, t.fim))
    return _renomear_por_ordem_de_fala(turnos)


def _renomear_por_ordem_de_fala(turnos: list[TurnoFalante]) -> list[TurnoFalante]:
    """Troca SPEAKER_00/01/... por FALANTE_01/02/... na ordem de aparição.

    O modelo numera as vozes de forma arbitrária. Para o usuário, o natural é
    que quem fala primeiro seja o "Falante 1".
    """
    mapa: dict[str, str] = {}
    for turno in turnos:
        if turno.falante not in mapa:
            mapa[turno.falante] = f"FALANTE_{len(mapa) + 1:02d}"
    return [TurnoFalante(t.inicio, t.fim, mapa[t.falante]) for t in turnos]


def atribuir_falantes(palavras: list[Palavra], turnos: list[TurnoFalante]) -> list[Palavra]:
    """Marca cada palavra com o falante do turno que mais se sobrepõe a ela.

    Função pura (não depende do WhisperX), o que a torna testável sozinha — e
    ela concentra a única regra realmente delicada do recurso.
    """
    if not turnos:
        return palavras

    resultado: list[Palavra] = []
    ultimo_falante: str | None = None

    for palavra in palavras:
        melhor_falante: str | None = None
        melhor_sobreposicao = 0.0

        for turno in turnos:
            if turno.inicio >= palavra.fim:
                break  # turnos estão ordenados; daqui para frente não sobrepõe
            sobreposicao = min(palavra.fim, turno.fim) - max(palavra.inicio, turno.inicio)
            if sobreposicao > melhor_sobreposicao:
                melhor_sobreposicao = sobreposicao
                melhor_falante = turno.falante

        # Palavra em silêncio ou fora de qualquer turno (respiração, ruído):
        # continua com quem estava falando, em vez de virar um falante fantasma.
        falante = melhor_falante or ultimo_falante
        if falante:
            ultimo_falante = falante

        resultado.append(
            Palavra(inicio=palavra.inicio, fim=palavra.fim, texto=palavra.texto, falante=falante)
        )

    return resultado


def rotulos_em_ordem(palavras: list[Palavra]) -> list[str]:
    """Rótulos de falante presentes, na ordem em que aparecem."""
    vistos: list[str] = []
    for palavra in palavras:
        if palavra.falante and palavra.falante not in vistos:
            vistos.append(palavra.falante)
    return vistos
