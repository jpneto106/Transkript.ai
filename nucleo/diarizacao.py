"""Identifica├º├úo de falantes (diariza├º├úo) com o WhisperX/pyannote.

O Whisper sabe O QUE foi dito e QUANDO; n├úo sabe QUEM falou. Este m├│dulo roda um
segundo modelo, que devolve os turnos de fala ("da 0:00 ├á 0:42 foi a voz A"), e
cruza esses turnos com as palavras j├í transcritas.

Duas decis├Áes de projeto importantes:

1. **O usu├írio final nunca precisa de conta no Hugging Face.** O modelo (32 MB)
   ├® baixado uma ├║nica vez pelo autor e vai junto do programa, em
   <app>/modelos. Para garantir que nenhuma instala├º├úo tente falar com a
   internet ÔÇö e falhe por falta de token ÔÇö, o modelo ├® carregado em modo
   estritamente local.

2. **A depend├¬ncia ├® opcional.** O WhisperX traz o PyTorch junto (~2,5 GB). Os
   imports ficam dentro das fun├º├Áes, e `diarizacao_disponivel()` permite ao
   aplicativo simplesmente n├úo oferecer o recurso quando ele n├úo est├í instalado,
   em vez de quebrar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .caminhos import RAIZ_APP
from .formatacao import Palavra

#: Reposit├│rio usado pelo WhisperX 3.8.x. Fixado aqui para o download do autor e
#: a checagem de disponibilidade falarem exatamente do mesmo modelo.
REPO_DIARIZACAO = "pyannote/speaker-diarization-community-1"

#: Progresso de 0.0 a 1.0 durante a diariza├º├úo.
CallbackProgressoDiarizacao = Callable[[float], None]


@dataclass
class TurnoFalante:
    """Um trecho cont├¡nuo em que uma ├║nica voz fala."""
    inicio: float
    fim: float
    falante: str


def _pasta_modelos() -> Path:
    return RAIZ_APP / "modelos"


def pasta_do_modelo() -> Path:
    return _pasta_modelos() / "hub" / ("models--" + REPO_DIARIZACAO.replace("/", "--"))


def modelo_baixado() -> bool:
    """True se o modelo de vozes j├í est├í na pasta do programa.

    Exige o config.yaml e os dois pesos (segmenta├º├úo e embedding) ÔÇö s├│ a pasta
    existir n├úo basta, porque um download interrompido deixa a pasta pela metade.
    """
    pasta = pasta_do_modelo()
    if not pasta.is_dir():
        return False
    tem_config = any(pasta.rglob("config.yaml"))
    pesos = {p.parent.name for p in pasta.rglob("pytorch_model.bin")}
    return tem_config and {"segmentation", "embedding"} <= pesos


def biblioteca_instalada() -> bool:
    """True se a biblioteca de vozes (e o PyTorch junto) est├í neste ambiente.

    Checamos o `pyannote.audio`, que ├® o que de fato carregamos ÔÇö ele vem junto
    do WhisperX, mas ├® dele que dependemos diretamente.
    """
    from importlib.util import find_spec

    try:
        return find_spec("pyannote.audio") is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def diarizacao_disponivel() -> bool:
    """S├│ oferecemos o recurso quando as duas pe├ºas existem."""
    return biblioteca_instalada() and modelo_baixado()


def caminho_local_do_modelo() -> Path | None:
    """Caminho do config.yaml baixado, ou None se o modelo n├úo est├í em disco.

    Apontar direto para este arquivo ├® o que dispensa por completo o Hugging
    Face em tempo de execu├º├úo ÔÇö sem rede, sem token, sem conta. Tentar carregar
    pelo nome do reposit├│rio faria a biblioteca consultar o site e receber 401,
    j├í que o reposit├│rio ├® fechado.

    (Definir HF_HUB_OFFLINE em tempo de execu├º├úo N├âO resolve: a biblioteca l├¬
    essa configura├º├úo no momento em que ├® importada.)
    """
    pasta = pasta_do_modelo() / "snapshots"
    if not pasta.is_dir():
        return None
    for snapshot in sorted(pasta.iterdir(), reverse=True):
        config = snapshot / "config.yaml"
        if config.is_file():
            return config
    return None


def carregar_pipeline(dispositivo: str):
    """Carrega o modelo de identifica├º├úo de vozes. Reutilize ÔÇö ├® caro de criar."""
    config = caminho_local_do_modelo()
    if config is None:
        raise RuntimeError(
            "O modelo de identifica├º├úo de vozes n├úo est├í instalado neste computador."
        )

    import torch
    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(str(config))
    if pipeline is None:
        raise RuntimeError(f"N├úo consegui carregar o modelo de vozes de {config}")
    return pipeline.to(torch.device(dispositivo))


def diarizar_arquivo(
    pipeline,
    arquivo: Path,
    *,
    num_falantes: int | None = None,
    ao_progredir: CallbackProgressoDiarizacao | None = None,
) -> list[TurnoFalante]:
    """Devolve os turnos de fala do arquivo, j├í com r├│tulos can├┤nicos.

    `num_falantes` for├ºa a quantidade quando o usu├írio sabe (mais preciso);
    None deixa o modelo descobrir sozinho.
    """
    import torch

    from .midia import TAXA_PADRAO, carregar_audio

    # Entregamos o ├íudio j├í decodificado em vez do caminho do arquivo: assim a
    # leitura passa pelo ffmpeg que embutimos, e n├úo pelo torchcodec (que exige
    # bibliotecas do FFmpeg em DLL, ausentes na nossa distribui├º├úo).
    amostras = carregar_audio(arquivo, TAXA_PADRAO)
    entrada = {
        "waveform": torch.from_numpy(amostras).unsqueeze(0),  # (canal, tempo)
        "sample_rate": TAXA_PADRAO,
    }

    argumentos = {}
    if num_falantes:
        argumentos["num_speakers"] = num_falantes
    if ao_progredir is not None:
        argumentos["hook"] = _GanchoProgresso(ao_progredir)

    saida = pipeline(entrada, **argumentos)
    anotacao = _extrair_anotacao(saida)

    turnos = [
        TurnoFalante(inicio=float(trecho.start), fim=float(trecho.end), falante=str(voz))
        for trecho, _, voz in anotacao.itertracks(yield_label=True)
    ]
    turnos.sort(key=lambda t: (t.inicio, t.fim))
    return _renomear_por_ordem_de_fala(turnos)


def _extrair_anotacao(saida):
    """Pega a anota├º├úo de falantes do que a pipeline devolveu.

    O pyannote 4 embrulha o resultado num objeto com duas vers├Áes: uma que
    admite duas pessoas falando ao mesmo tempo e outra **exclusiva**, sem
    sobreposi├º├úo. Preferimos a exclusiva: o Whisper produz um texto linear, e
    cada palavra s├│ pode pertencer a uma voz. Vers├Áes antigas devolviam a
    anota├º├úo direto ÔÇö por isso o retorno simples tamb├®m ├® aceito.
    """
    for atributo in ("exclusive_speaker_diarization", "speaker_diarization"):
        anotacao = getattr(saida, atributo, None)
        if anotacao is not None and hasattr(anotacao, "itertracks"):
            return anotacao
    if hasattr(saida, "itertracks"):
        return saida
    raise RuntimeError(
        f"Formato inesperado do modelo de vozes: {type(saida).__name__}"
    )


class _GanchoProgresso:
    """Traduz o progresso interno do pyannote para um n├║mero de 0 a 1.

    O pyannote avisa por etapas (segmenta├º├úo, embeddings, agrupamento), cada uma
    com seu pr├│prio contador. Como n├úo h├í uma fra├º├úo global pronta, informamos o
    andamento dentro da etapa atual ÔÇö o suficiente para a barra n├úo ficar parada.
    """

    ETAPAS = ("segmentation", "embeddings", "speaker_counting", "discrete_diarization")

    def __init__(self, ao_progredir: CallbackProgressoDiarizacao):
        self._ao_progredir = ao_progredir

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def __call__(self, nome_etapa, artefato, file=None, total=None, completed=None, **_):
        if not total or completed is None:
            return
        try:
            indice = self.ETAPAS.index(nome_etapa)
        except ValueError:
            indice = 0
        fracao_etapa = min(1.0, completed / total)
        self._ao_progredir((indice + fracao_etapa) / len(self.ETAPAS))


def _renomear_por_ordem_de_fala(turnos: list[TurnoFalante]) -> list[TurnoFalante]:
    """Troca SPEAKER_00/01/... por FALANTE_01/02/... na ordem de apari├º├úo.

    O modelo numera as vozes de forma arbitr├íria. Para o usu├írio, o natural ├®
    que quem fala primeiro seja o "Falante 1".
    """
    mapa: dict[str, str] = {}
    for turno in turnos:
        if turno.falante not in mapa:
            mapa[turno.falante] = f"FALANTE_{len(mapa) + 1:02d}"
    return [TurnoFalante(t.inicio, t.fim, mapa[t.falante]) for t in turnos]


def atribuir_falantes(palavras: list[Palavra], turnos: list[TurnoFalante]) -> list[Palavra]:
    """Marca cada palavra com o falante do turno que mais se sobrep├Áe a ela.

    Fun├º├úo pura (n├úo depende do WhisperX), o que a torna test├ível sozinha ÔÇö e
    ela concentra a ├║nica regra realmente delicada do recurso.
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
                break  # turnos est├úo ordenados; daqui para frente n├úo sobrep├Áe
            sobreposicao = min(palavra.fim, turno.fim) - max(palavra.inicio, turno.inicio)
            if sobreposicao > melhor_sobreposicao:
                melhor_sobreposicao = sobreposicao
                melhor_falante = turno.falante

        # Palavra em sil├¬ncio ou fora de qualquer turno (respira├º├úo, ru├¡do):
        # continua com quem estava falando, em vez de virar um falante fantasma.
        falante = melhor_falante or ultimo_falante
        if falante:
            ultimo_falante = falante

        resultado.append(
            Palavra(inicio=palavra.inicio, fim=palavra.fim, texto=palavra.texto, falante=falante)
        )

    return resultado


def rotulos_em_ordem(palavras: list[Palavra]) -> list[str]:
    """R├│tulos de falante presentes, na ordem em que aparecem."""
    vistos: list[str] = []
    for palavra in palavras:
        if palavra.falante and palavra.falante not in vistos:
            vistos.append(palavra.falante)
    return vistos
