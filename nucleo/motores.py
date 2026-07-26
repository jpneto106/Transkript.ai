"""Motores de transcrição: Whisper (faster-whisper) e NVIDIA (NeMo via ONNX).

O programa aceita modelos de fornecedores diferentes. Cada motor sabe carregar
os seus modelos e devolver o resultado no formato comum do projeto
(`ResultadoTranscricao`), de modo que blocos, legendas e diarização funcionam
igual para todos.

O nome interno do modelo é único no catálogo (ver `nucleo/constantes.py`), então
basta ele para descobrir qual motor usar.

Sobre o motor NVIDIA: usamos os modelos exportados para **ONNX**, e não o
`nemo_toolkit`. Motivos concretos, medidos nesta máquina:

- o NeMo exige compilar dependências em C++ (não há wheel pronto para Python
  3.13 no Windows) e traria ~70 pacotes;
- o caminho ONNX precisa de **um único** pacote novo, porque o `onnxruntime` já
  vem com o faster-whisper;
- o Parakeet transcreveu 58s de português em 3,2s — na CPU. É mais rápido que o
  Whisper `small` na GPU.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from .blocos import montar_blocos
from .constantes import MOTOR_NVIDIA, MOTOR_WHISPER, motor_do_modelo, repositorio_do_modelo
from .formatacao import Palavra, ResultadoTranscricao
from .transcricao import (
    CallbackProgresso,
    EventoProgresso,
    TranscricaoCancelada,
    VerificadorCancelamento,
)

#: Taxa que os modelos de fala esperam.
_TAXA = 16000


# --------------------------------------------------------------------- Whisper

def whisper_disponivel() -> bool:
    from importlib.util import find_spec

    return find_spec("faster_whisper") is not None


def _whisper_carregar(nome: str, dispositivo: str, compute_type: str):
    from .transcricao import carregar_modelo

    return carregar_modelo(nome, dispositivo, compute_type)


def _whisper_transcrever(modelo, arquivo: Path, **opcoes) -> ResultadoTranscricao:
    from .transcricao import transcrever_arquivo

    return transcrever_arquivo(
        modelo,
        arquivo,
        idioma=opcoes["idioma"],
        tarefa=opcoes["tarefa"],
        beam_size=opcoes["beam_size"],
        vad_filter=opcoes["vad_filter"],
        max_caracteres=opcoes["max_caracteres"],
        max_duracao=opcoes["max_duracao"],
        initial_prompt=opcoes.get("initial_prompt"),
        ao_progredir=opcoes.get("ao_progredir"),
        cancelado=opcoes.get("cancelado"),
    )


# ---------------------------------------------------------------------- NVIDIA

def nvidia_disponivel() -> bool:
    from importlib.util import find_spec

    return find_spec("onnx_asr") is not None


def _nvidia_carregar(nome: str, dispositivo: str, compute_type: str):
    import onnx_asr
    import onnxruntime as ort

    from .constantes import NOME_ONNX_ASR

    nome_onnx = NOME_ONNX_ASR.get(nome)
    if nome_onnx is None:
        raise RuntimeError(f"Modelo NVIDIA desconhecido: {nome}")

    # Sem GPU no onnxruntime, a versão int8 é bem mais rápida (e baixa ~640 MB
    # em vez de 3 GB). Com GPU disponível, vale a precisão cheia.
    tem_gpu = "CUDAExecutionProvider" in ort.get_available_providers()
    return onnx_asr.load_model(nome_onnx, quantization=None if tem_gpu else "int8")


# Medido nesta máquina com o parakeet-v3 (áudio de 8 min, int8 na CPU):
#     60s -> 5,9s | 120s -> 8,1s | 180s -> 13,9s | 240s -> 32,3s
#    300s -> 172s (!) | 420s -> falha do onnxruntime
# O custo da atenção cresce ao quadrado, então trechos longos não só arriscam
# estourar como ficam MUITO mais lentos. 120s é o ponto mais eficiente e fica
# bem longe do limite.
_JANELA_SEGUNDOS = 120.0

#: Quanto procurar por silêncio antes do fim da janela, para cortar numa pausa.
_BUSCA_SILENCIO_SEGUNDOS = 8.0

#: Tamanho do quadro usado para medir volume ao procurar a pausa.
_QUADRO_SEGUNDOS = 0.02


def _ponto_mais_silencioso(amostras, inicio: int, fim: int, taxa: int) -> int:
    """Índice do trecho mais silencioso entre `inicio` e `fim`.

    Serve para cortar o áudio numa pausa em vez de no meio de uma palavra. Se
    não houver pausa nenhuma (fala contínua), devolve o ponto mais quieto que
    encontrar — o corte acontece de qualquer jeito, porque o limite do modelo
    não é negociável.
    """
    import numpy as np

    quadro = max(1, int(_QUADRO_SEGUNDOS * taxa))
    trecho = amostras[inicio:fim]
    if len(trecho) < quadro * 2:
        return fim

    sobra = len(trecho) % quadro
    if sobra:
        trecho = trecho[:-sobra]
    quadros = trecho.reshape(-1, quadro)
    energia = np.abs(quadros).mean(axis=1)
    return inicio + int(energia.argmin()) * quadro


def _fatiar_audio(amostras, taxa: int) -> list[tuple[int, int]]:
    """Divide o áudio em pedaços que o modelo aguenta, cortando em pausas.

    O silêncio é apenas a PREFERÊNCIA de onde cortar; o limite de duração é
    obrigatório. Assim funciona também em áudio sem pausa alguma — uma narração
    corrida, por exemplo.
    """
    total = len(amostras)
    janela = int(_JANELA_SEGUNDOS * taxa)
    if total <= janela:
        return [(0, total)]

    margem = int(_BUSCA_SILENCIO_SEGUNDOS * taxa)
    pedacos: list[tuple[int, int]] = []
    inicio = 0
    while total - inicio > janela:
        fim_maximo = inicio + janela
        # Procura a pausa só no fim da janela: cortar antes desperdiçaria a
        # capacidade do modelo e criaria pedaços curtos demais.
        corte = _ponto_mais_silencioso(amostras, fim_maximo - margem, fim_maximo, taxa)
        if corte <= inicio:
            corte = fim_maximo
        pedacos.append((inicio, corte))
        inicio = corte
    pedacos.append((inicio, total))
    return pedacos


def _tokens_para_palavras(tokens, tempos, duracao: float) -> list[Palavra]:
    """Junta os pedaços de palavra devolvidos pelo modelo em palavras inteiras.

    O modelo devolve sub-tokens ('  y', 'out', 'u', 'ber') com o instante de
    início de cada um. A convenção é que um token iniciado por espaço começa uma
    palavra nova. O fim de cada palavra é o início da seguinte — o modelo não
    informa fim, e essa aproximação é suficiente para montar blocos e legendas.
    """
    palavras: list[Palavra] = []
    atual = ""
    inicio_atual = 0.0

    for token, instante in zip(tokens, tempos):
        if token.startswith(" ") and atual:
            palavras.append(Palavra(inicio=inicio_atual, fim=float(instante), texto=atual))
            atual, inicio_atual = token, float(instante)
        else:
            if not atual:
                inicio_atual = float(instante)
            atual += token

    if atual:
        palavras.append(Palavra(inicio=inicio_atual, fim=duracao, texto=atual))

    # Garante fim >= início mesmo com timestamps repetidos.
    for palavra in palavras:
        if palavra.fim < palavra.inicio:
            palavra.fim = palavra.inicio
    return palavras


def _nvidia_transcrever(modelo, arquivo: Path, **opcoes) -> ResultadoTranscricao:
    from .midia import carregar_audio

    cancelado: VerificadorCancelamento | None = opcoes.get("cancelado")
    ao_progredir: CallbackProgresso | None = opcoes.get("ao_progredir")

    amostras = carregar_audio(arquivo, _TAXA)
    duracao = len(amostras) / _TAXA

    if cancelado is not None and cancelado():
        raise TranscricaoCancelada()

    if ao_progredir is not None:
        ao_progredir(EventoProgresso(arquivo, 0.0, duracao))

    inicio = time.perf_counter()
    com_tempos = modelo.with_timestamps()
    idioma = opcoes.get("idioma") or None

    # Áudio longo é processado em pedaços: o modelo tem um teto rígido e, bem
    # antes dele, fica desproporcionalmente lento. Fatiar também dá progresso
    # de verdade ao usuário, em vez de uma barra parada.
    pedacos = _fatiar_audio(amostras, _TAXA)
    palavras: list[Palavra] = []

    for indice, (ini, fim) in enumerate(pedacos):
        if cancelado is not None and cancelado():
            raise TranscricaoCancelada()

        deslocamento = ini / _TAXA
        bruto = com_tempos.recognize(
            amostras[ini:fim], sample_rate=_TAXA, language=idioma
        )
        duracao_pedaco = (fim - ini) / _TAXA
        for palavra in _tokens_para_palavras(
            getattr(bruto, "tokens", []), getattr(bruto, "timestamps", []), duracao_pedaco
        ):
            # Os tempos voltam relativos ao pedaço; trazemos para o áudio inteiro.
            palavra.inicio += deslocamento
            palavra.fim += deslocamento
            palavras.append(palavra)

        if ao_progredir is not None:
            ao_progredir(EventoProgresso(arquivo, fim / _TAXA, duracao))

    tempo_processamento = time.perf_counter() - inicio

    resultado = ResultadoTranscricao(
        arquivo=arquivo,
        # Estes modelos não detectam o idioma: devolvemos o que foi pedido.
        idioma=opcoes.get("idioma") or "",
        probabilidade_idioma=1.0 if opcoes.get("idioma") else 0.0,
        duracao=duracao,
        tempo_processamento=tempo_processamento,
    )
    resultado.palavras = palavras
    resultado.segmentos = montar_blocos(
        palavras,
        max_caracteres=opcoes["max_caracteres"],
        max_duracao=opcoes["max_duracao"],
    )

    return resultado


# --------------------------------------------------------------------- registro

_MOTORES: dict[str, dict[str, Callable]] = {
    MOTOR_WHISPER: {
        "disponivel": whisper_disponivel,
        "carregar": _whisper_carregar,
        "transcrever": _whisper_transcrever,
        "rotulo": lambda: "Whisper",
    },
    MOTOR_NVIDIA: {
        "disponivel": nvidia_disponivel,
        "carregar": _nvidia_carregar,
        "transcrever": _nvidia_transcrever,
        "rotulo": lambda: "NVIDIA",
    },
}


def motores_disponiveis() -> dict[str, bool]:
    """Quais motores este computador consegue usar."""
    return {chave: motor["disponivel"]() for chave, motor in _MOTORES.items()}


def carregar_modelo_do_motor(nome: str, dispositivo: str, compute_type: str):
    """Carrega o modelo pelo nome, escolhendo o motor certo automaticamente."""
    motor = motor_do_modelo(nome)
    definicao = _MOTORES[motor]
    if not definicao["disponivel"]():
        raise RuntimeError(
            f"O motor {definicao['rotulo']()} não está instalado neste computador."
        )
    return definicao["carregar"](nome, dispositivo, compute_type)


def transcrever_com_motor(nome_modelo: str, modelo, arquivo: Path, **opcoes) -> ResultadoTranscricao:
    """Transcreve usando o motor a que o modelo pertence."""
    return _MOTORES[motor_do_modelo(nome_modelo)]["transcrever"](modelo, arquivo, **opcoes)
