"""Catálogo de provedores de IA para resumo (Etapa 7 do plano v4-leve).

Os provedores se dividem em dois grupos:

- **OpenAI-compatíveis**: falam o mesmo protocolo que o OpenAI
  ``/v1/chat/completions``. Cobre LM Studio, Ollama (com OpenAI-compat),
  Groq, OpenRouter, Mistral, Together, OpenAI nativo, e qualquer servidor
  que implemente esse padrão.

- **Anthropic (Claude)**: API própria, formato de mensagens diferente.

A escolha do usuário é por nome curto (``lm_studio``, ``claude`` etc.); o
catálogo converte para ``ConfigResumo`` com URL, modelo padrão e o nome do
grupo de protocolo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProvedorPreset:
    """Como falar com um provedor: identificador, rótulo, URL, modelo padrão."""

    chave: str
    rotulo: str
    provedor: str          # "openai_compat" ou "anthropic"
    url_base: str
    modelo_padrao: str = ""
    chave_padrao: str = ""  # alguns locais não exigem auth (ex.: LM Studio)


# Ordem na UI segue esta lista. Cada entrada aparece como opção no seletor.
PROVEDORES: list[ProvedorPreset] = [
    ProvedorPreset(
        chave="lm_studio",
        rotulo="LM Studio (local)",
        provedor="openai_compat",
        url_base="http://localhost:1234/v1",
        modelo_padrao="",
        chave_padrao="lm-studio",
    ),
    ProvedorPreset(
        chave="ollama",
        rotulo="Ollama (local)",
        provedor="openai_compat",
        url_base="http://localhost:11434/v1",
        modelo_padrao="llama3.2",
        chave_padrao="ollama",
    ),
    ProvedorPreset(
        chave="groq",
        rotulo="Groq (nuvem)",
        provedor="openai_compat",
        url_base="https://api.groq.com/openai/v1",
        modelo_padrao="llama-3.3-70b-versatile",
    ),
    ProvedorPreset(
        chave="openrouter",
        rotulo="OpenRouter (nuvem)",
        provedor="openai_compat",
        url_base="https://openrouter.ai/api/v1",
        modelo_padrao="openai/gpt-4o-mini",
    ),
    ProvedorPreset(
        chave="mistral",
        rotulo="Mistral (nuvem)",
        provedor="openai_compat",
        url_base="https://api.mistral.ai/v1",
        modelo_padrao="mistral-small-latest",
    ),
    ProvedorPreset(
        chave="openai",
        rotulo="OpenAI (nuvem)",
        provedor="openai_compat",
        url_base="https://api.openai.com/v1",
        modelo_padrao="gpt-4o-mini",
    ),
    ProvedorPreset(
        chave="claude",
        rotulo="Claude (Anthropic)",
        provedor="anthropic",
        url_base="https://api.anthropic.com",
        modelo_padrao="claude-3-5-sonnet-latest",
    ),
    ProvedorPreset(
        chave="personalizado",
        rotulo="Personalizado (compatível com OpenAI)",
        provedor="openai_compat",
        url_base="",
        modelo_padrao="",
    ),
]


def provedor_por_chave(chave: str) -> ProvedorPreset | None:
    """Devolve o preset pelo identificador curto; None se não achar."""
    for p in PROVEDORES:
        if p.chave == chave:
            return p
    return None


# Estilos de resumo cobertos pelo ``resumir``. Cada um traduz um prompt diferente.
@dataclass(frozen=True)
class EstiloResumo:
    chave: str
    rotulo: str
    instrucao: str


ESTILOS: list[EstiloResumo] = [
    EstiloResumo(
        chave="curto",
        rotulo="Resumo curto (1-2 parágrafos)",
        instrucao="Em 1 ou 2 parágrafos, capture a ideia central e os pontos de virada.",
    ),
    EstiloResumo(
        chave="topicos",
        rotulo="Tópicos (bullets)",
        instrucao="Liste em bullets os principais pontos discutidos, na ordem em que aparecem.",
    ),
    EstiloResumo(
        chave="frases_chave",
        rotulo="Frases-chave (citações curtas)",
        instrucao="Selecione as frases mais importantes do texto, transcritas literalmente. Atribua a frase a quem fala, quando houver.",
    ),
    EstiloResumo(
        chave="executivo",
        rotulo="Resumo executivo",
        instrucao="Tom profissional, audiência executiva. Máximo de 5 bullets. Inclua decisão recomendada se houver.",
    ),
]


def estilo_por_chave(chave: str) -> EstiloResumo | None:
    for s in ESTILOS:
        if s.chave == chave:
            return s
    return None
