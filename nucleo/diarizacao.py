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
    """True se a biblioteca de vozes (e o PyTorch junto) está neste ambiente.

    Checamos o `pyannote.audio`, que é o que de fato carregamos — ele vem junto
    do WhisperX, mas é dele que dependemos diretamente.
    """
    from importlib.util import find_spec

    try:
        return find_spec("pyannote.audio") is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def baixar_modelo() -> Path | None:
    """Baixa o modelo de diarização do Hugging Face se ainda não estiver em disco.

    Usa ``huggingface_hub.snapshot_download`` para colocar os arquivos no
    diretório padrão do HF Hub (``<raiz>/modelos/hub/...``). O modelo
    ``pyannote/speaker-diarization-community-1`` é o pipeline aberto do
    pyannote (não-gated), mas seus sub-modelos (segmentação, embedding)
    podem pedir login do Hugging Face em alguns deles — qualquer erro é
    propagado com mensagem clara.

    Devolve o caminho do ``config.yaml`` baixado, ou ``None`` se já existia
    antes (o que também é sucesso: nada a fazer).
    """
    if modelo_baixado():
        return caminho_local_do_modelo()

    from huggingface_hub import snapshot_download

    cache = RAIZ_APP / "modelos"
    cache.mkdir(parents=True, exist_ok=True)

    try:
        snapshot_download(
            repo_id=REPO_DIARIZACAO,
            cache_dir=str(cache),
            allow_patterns=["*.yaml", "pytorch_model.bin", "config.yaml"],
        )
    except Exception as erro:
        raise RuntimeError(
            "Não consegui baixar o modelo de identificação de vozes. "
            "Ele vive em huggingface.co/pyannote/speaker-diarization-community-1. "
            f"Detalhe: {erro!r}"
        ) from erro

    return caminho_local_do_modelo()


def diarizacao_disponivel() -> bool:
    """True se a biblioteca está instalada.

    O modelo é baixado sob demanda em ``carregar_pipeline`` — o usuário não
    precisa de um instalador para usá-lo. Se quiser conferir o estado do
    modelo em disco, chame ``modelo_baixado()`` diretamente.
    """
    return biblioteca_instalada()


def caminho_local_do_modelo() -> Path | None:
    """Caminho do config.yaml baixado, ou None se o modelo não está em disco.

    Apontar direto para este arquivo é o que dispensa por completo o Hugging
    Face em tempo de execução — sem rede, sem token, sem conta. Tentar carregar
    pelo nome do repositório faria a biblioteca consultar o site e receber 401,
    já que o repositório é fechado.

    (Definir HF_HUB_OFFLINE em tempo de execução NÃO resolve: a biblioteca lê
    essa configuração no momento em que é importada.)
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
    """Carrega o modelo de identificação de vozes. Reutilize — é caro de criar.

    Se o modelo ainda não estiver em disco, baixa agora (com rede). Em rede
    sem acesso ao Hugging Face, ``baixar_modelo`` levanta ``RuntimeError``
    com instrução clara.

    Se o dispositivo pedido for ``"cuda"`` mas o PyTorch instalado não tiver
    suporte a CUDA (PyTorch CPU-only), cai automaticamente para ``"cpu"``.
    O Whisper roda acelerado via ctranslate2, que tem CUDA à parte; o
    pyannote depende do PyTorch, e essa queda evita que a interface mostre
    erros silenciosos.
    """
    config = caminho_local_do_modelo()
    if config is None:
        config = baixar_modelo()
    if config is None:
        raise RuntimeError(
            "O modelo de identificação de vozes não está instalado neste computador "
            "e não foi possível baixá-lo agora."
        )

    import torch

    dispositivo_real = dispositivo
    if dispositivo in ("cuda", "auto") and not torch.cuda.is_available():
        dispositivo_real = "cpu"

    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(str(config))
    if pipeline is None:
        raise RuntimeError(f"Não consegui carregar o modelo de vozes de {config}")
    return pipeline.to(torch.device(dispositivo_real))


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
    import torch

    from .midia import TAXA_PADRAO, carregar_audio

    # Entregamos o áudio já decodificado em vez do caminho do arquivo: assim a
    # leitura passa pelo ffmpeg que embutimos, e não pelo torchcodec (que exige
    # bibliotecas do FFmpeg em DLL, ausentes na nossa distribuição).
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
    """Pega a anotação de falantes do que a pipeline devolveu.

    O pyannote 4 embrulha o resultado num objeto com duas versões: uma que
    admite duas pessoas falando ao mesmo tempo e outra **exclusiva**, sem
    sobreposição. Preferimos a exclusiva: o Whisper produz um texto linear, e
    cada palavra só pode pertencer a uma voz. Versões antigas devolviam a
    anotação direto — por isso o retorno simples também é aceito.
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
    """Traduz o progresso interno do pyannote para um número de 0 a 1.

    O pyannote avisa por etapas (segmentação, embeddings, agrupamento), cada uma
    com seu próprio contador. Como não há uma fração global pronta, informamos o
    andamento dentro da etapa atual — o suficiente para a barra não ficar parada.
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
