"""Reagrupamento das palavras transcritas em blocos legíveis de tamanho controlado."""

from __future__ import annotations

from .constantes import FINALIZADORES_DE_FRASE
from .formatacao import Palavra, Segmento


def montar_blocos(palavras: list[Palavra], max_caracteres: int, max_duracao: float) -> list[Segmento]:
    """Reagrupa palavras (com timestamp individual) em blocos menores para
    legenda/leitura, respeitando um limite de caracteres e de duração por bloco."""
    blocos: list[Segmento] = []
    atual: list[Palavra] = []

    def texto_de(lista: list[Palavra]) -> str:
        return "".join(p.texto for p in lista).strip()

    def fechar_bloco() -> None:
        if not atual:
            return
        blocos.append(
            Segmento(
                inicio=atual[0].inicio,
                fim=atual[-1].fim,
                texto=texto_de(atual),
                falante=atual[0].falante,
            )
        )
        atual.clear()

    for palavra in palavras:
        # Troca de falante sempre encerra o bloco, mesmo curto: misturar duas
        # vozes num mesmo bloco tornaria a legenda e o texto ilegíveis.
        if atual and palavra.falante != atual[-1].falante:
            fechar_bloco()

        candidato = atual + [palavra]
        texto_candidato = texto_de(candidato)
        duracao_candidato = palavra.fim - candidato[0].inicio

        if atual and (len(texto_candidato) > max_caracteres or duracao_candidato > max_duracao):
            fechar_bloco()

        atual.append(palavra)

        texto_atual = texto_de(atual)
        if texto_atual.endswith(FINALIZADORES_DE_FRASE) and len(texto_atual) > max_caracteres * 0.4:
            fechar_bloco()

    fechar_bloco()
    return blocos


def extrair_palavras(segmentos_whisper) -> list[Palavra]:
    palavras: list[Palavra] = []
    for seg in segmentos_whisper:
        if seg.words:
            palavras.extend(Palavra(inicio=w.start, fim=w.end, texto=w.word) for w in seg.words)
        else:
            palavras.append(Palavra(inicio=seg.start, fim=seg.end, texto=f" {seg.text.strip()}"))
    return palavras
