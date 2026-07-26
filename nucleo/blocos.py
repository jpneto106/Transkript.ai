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


# ============================================================ presets (Etapa 7)

#: Presets de tamanho de bloco para o ``montar_blocos``. Cada preset é um par
#: ``(max_caracteres, max_duracao)`` calibrado para um caso de uso diferente.
#: O frontend expõe isso na aba "Nova transcrição"; mudanças aqui viram ajuste
#: sem precisar mexer no código da interface.
PRESETS_BLOCOS: dict[str, tuple[int, float]] = {
    # Padrão: vídeos longos, podcasts, palestras. Limite confortável para
    # legendas desktop e leitura corrida no editor.
    "padrao":      (80, 4.0),
    # Texto corrido mais largo: monitor grande, leitura rápida.
    "longo":       (90, 5.0),
    # Frase curta por bloco: ideal para legendagem tradicional em PT-BR.
    "curto":       (50, 2.5),
    # Reel / Short / TikTok: legenda tem que caber em 2 linhas no celular e
    # não pode ficar mais de ~1,4 s na tela. Junta com o Vibe.
    "reel":        (24, 1.4),
    # Bloco bem largo para uma frase inteira por linha: usa o limite de
    # duração como o teto principal, não o número de caracteres.
    "frase":       (120, 7.0),
}


def parametros_do_preset(nome: str) -> tuple[int, float]:
    """Devolve ``(max_caracteres, max_duracao)`` para o preset, ou o padrão se não conhecer."""
    return PRESETS_BLOCOS.get(nome, PRESETS_BLOCOS["padrao"])


def montar_blocos_com_preset(palavras: list[Palavra], nome_preset: str) -> list[Segmento]:
    """Atalho para ``montar_blocos`` usando um preset nomeado."""
    max_caracteres, max_duracao = parametros_do_preset(nome_preset)
    return montar_blocos(palavras, max_caracteres=max_caracteres, max_duracao=max_duracao)
