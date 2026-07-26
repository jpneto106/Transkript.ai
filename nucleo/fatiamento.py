"""Fatiamento de áudio em pedaços que cabem no teto do motor de transcrição.

Isolado de ``nucleo/motores.py`` (Etapa 1 do plano ``ol-um-outro-agente-graceful-oasis.md``).
A lógica vivia como função privada dentro do motor NVIDIA; virar módulo
aberto permite reuso (futuro presets de reel da Etapa 7, eventual motor
Sona, e ferramentas que precisem cortar áudio antes de transcrever) sem
carregar o motor inteiro.

Dois modos estão previstos:

- ``"silencio"`` (atual, sempre funciona): detecção de pausa por energia
  da amostra. Simples, zero dependência extra, suficiente para a grande
  maioria dos áudios.
- ``"vad"`` (contrato para a Etapa 7): silero-vad, cortes mais próximos
  das pausas de fala real. Hoje levanta ``RuntimeError`` com a instrução
  de instalar ``pip install silero-vad``; quando a Etapa 7 for entregue,
  a integração entra aqui sem precisar refatorar quem chama.

Os invariantes de fatiamento são cobertos por ``testes/test_fatiamento.py``:
áudio curto não é dividido, nenhum pedaço ultrapassa o limite de duração,
pedacos se encostam sem lacuna nem sobreposição, e o corte prefere uma
pausa quando ela existe dentro da janela de busca.
"""

from __future__ import annotations

from importlib.util import find_spec

#: Limite padrão de cada fatia, em segundos. Compatível com o teto medido
#: dos modelos NVIDIA (Parakeet/Canary): 120 s é o ponto mais eficiente e
#: fica bem abaixo do teto rígido onde o onnxruntime falha.
JANELA_SEGUNDOS_PADRAO = 120.0

#: Janela, antes do fim da fatia, em que procuramos uma pausa. Pequena para
#: não desperdiçar a capacidade do modelo e não criar pedaços curtos demais.
BUSCA_SILENCIO_SEGUNDOS = 8.0

#: Tamanho do quadro usado para medir volume (RMS da janela).
QUADRO_SEGUNDOS = 0.02


def _ponto_mais_silencioso(amostras, inicio: int, fim: int, taxa: int) -> int:
    """Índice do trecho mais silencioso entre ``inicio`` e ``fim`` (em amostras).

    Serve para cortar o áudio numa pausa em vez de no meio de uma palavra. Se
    não houver pausa nenhuma (fala contínua), devolve o ponto mais quieto que
    encontrar — o corte acontece de qualquer jeito, porque o limite do modelo
    não é negociável.
    """
    import numpy as np

    quadro = max(1, int(QUADRO_SEGUNDOS * taxa))
    trecho = amostras[inicio:fim]
    if len(trecho) < quadro * 2:
        return fim

    sobra = len(trecho) % quadro
    if sobra:
        trecho = trecho[:-sobra]
    quadros = trecho.reshape(-1, quadro)
    energia = np.abs(quadros).mean(axis=1)
    return inicio + int(energia.argmin()) * quadro


def _silero_vad_disponivel() -> bool:
    try:
        return find_spec("silero_vad") is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def fatiar_por_silencio(
    amostras,
    taxa: int,
    *,
    janela_segundos: float = JANELA_SEGUNDOS_PADRAO,
    busca_silencio_segundos: float = BUSCA_SILENCIO_SEGUNDOS,
) -> list[tuple[int, int]]:
    """Divide ``amostras`` em pedaços de até ``janela_segundos``, cortando em pausas.

    O silêncio é apenas a PREFERÊNCIA de onde cortar; o limite de duração é
    obrigatório. Assim funciona também em áudio sem pausa alguma — uma narração
    corrida, por exemplo.

    Retorna uma lista de pares ``(inicio, fim)`` em índices de amostra, cobrindo
    todo o áudio sem lacuna nem sobreposição.
    """
    total = len(amostras)
    janela = int(janela_segundos * taxa)
    if total <= janela:
        return [(0, total)]

    margem = int(busca_silencio_segundos * taxa)
    pedacos: list[tuple[int, int]] = []
    inicio = 0
    while total - inicio > janela:
        fim_maximo = inicio + janela
        corte = _ponto_mais_silencioso(amostras, fim_maximo - margem, fim_maximo, taxa)
        if corte <= inicio:
            corte = fim_maximo
        pedacos.append((inicio, corte))
        inicio = corte
    pedacos.append((inicio, total))
    return pedacos


def fatiar_por_vad(
    amostras,
    taxa: int,
    *,
    janela_segundos: float = JANELA_SEGUNDOS_PADRAO,
) -> list[tuple[int, int]]:
    """Modo "vad": cortes guiados por detecção de atividade de voz (silero-vad).

    Hoje a integração real ainda não foi escrita — o método existe como
    contrato para a Etapa 7 do plano (presets de reel) e para o eventual
    motor Sona. Levanta ``RuntimeError`` com a instrução de instalar o
    pacote opcional. Quando a integração entrar, mantém-se a mesma
    assinatura e os mesmos invariantes de fatiamento (sem lacuna, sem
    ultrapassar a janela).
    """
    if not _silero_vad_disponivel():
        raise RuntimeError(
            "O modo 'vad' exige o pacote opcional 'silero-vad'. "
            "Instale com:  pip install silero-vad"
        )
    raise NotImplementedError(
        "Integração silero-vad ainda não escrita. "
        "Use modo='silencio' por enquanto."
    )


def fatiar(
    amostras,
    taxa: int,
    *,
    modo: str = "silencio",
    janela_segundos: float = JANELA_SEGUNDOS_PADRAO,
) -> list[tuple[int, int]]:
    """Ponto de entrada único do fatiamento.

    ``modo`` aceita:

    - ``"silencio"``: detecção de pausa por energia (sempre funciona).
    - ``"vad"``: silero-vad (requer ``pip install silero-vad``; quando
      integrado, será o padrão para o preset "reel" da Etapa 7).
    """
    if modo == "silencio":
        return fatiar_por_silencio(amostras, taxa, janela_segundos=janela_segundos)
    if modo == "vad":
        return fatiar_por_vad(amostras, taxa, janela_segundos=janela_segundos)
    raise ValueError(f"modo de fatiamento desconhecido: {modo!r} (use 'silencio' ou 'vad')")


__all__ = [
    "JANELA_SEGUNDOS_PADRAO",
    "BUSCA_SILENCIO_SEGUNDOS",
    "QUADRO_SEGUNDOS",
    "fatiar",
    "fatiar_por_silencio",
    "fatiar_por_vad",
]
