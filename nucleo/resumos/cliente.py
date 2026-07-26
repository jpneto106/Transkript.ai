"""Cliente para resumo por IA (Etapa 7 do plano v4-leve).

Ponto de entrada: ``resumir(texto, config)``. Dispara para o provedor
escolhido e devolve o resumo em texto simples. Erros do provedor saem como
``RuntimeError`` com mensagem útil (sem dump de stacktrace na interface).

A configuração vive em ``ConfigResumo``. Persistência é responsabilidade de
quem chama — esta função não toca em disco.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .provedores import PROVEDORES, EstiloResumo, ProvedorPreset, provedor_por_chave


@dataclass
class ConfigResumo:
    """Tudo o que ``resumir`` precisa saber."""

    chave_provedor: str           # "lm_studio" | "ollama" | "groq" | "claude" | ...
    url_base: str = ""            # sobrescreve o preset se preenchido
    chave_api: str = ""           # o usuário cola aqui; nunca logamos nem exibimos inteira
    modelo: str = ""              # sobrescreve o preset se preenchido
    estilo: str = "curto"         # uma chave de ``EstiloResumo``
    idioma: str = "pt-BR"         # usado na instrução do system prompt
    max_tokens: int = 1024        # teto da resposta
    temperatura: float = 0.3      # criatividade (0 = determinístico, 1 = criativo)


#: Prompt de sistema enviado a TODOS os provedores. Tem a marca do produto
#: para fins de rastreabilidade caso o usuário precise pedir suporte.
SYSTEM_PROMPT_BASE = (
    "Você resume transcrições de vídeo/áudio no idioma {idioma}. "
    "Devolva APENAS o resumo, sem introdução como 'Aqui vai o resumo'. "
    "Siga o estilo pedido. Se o texto não tiver conteúdo resgatável, "
    "devolva exatamente: (texto insuficiente para resumir)."
)


def _prompt_sistema(config: ConfigResumo) -> str:
    return SYSTEM_PROMPT_BASE.format(idioma=config.idioma)


def _prompt_usuario(texto: str, estilo: EstiloResumo) -> str:
    return (
        f"Estilo pedido: {estilo.instrucao}\n\n"
        f"Transcrição a resumir (use apenas este texto, sem conhecimento externo):\n\n"
        f"{texto}"
    )


def _montar_prompts(config: ConfigResumo, texto: str) -> tuple[str, str]:
    from .provedores import estilo_por_chave
    estilo = estilo_por_chave(config.estilo)
    if estilo is None:
        raise RuntimeError(f"Estilo de resumo desconhecido: {config.estilo!r}")
    return _prompt_sistema(config), _prompt_usuario(texto, estilo)


def _resolver_preset(config: ConfigResumo) -> ProvedorPreset:
    """Aplica overrides do usuário em cima do preset; se não houver preset, usa ``openai_compat`` com o que veio."""
    preset = provedor_por_chave(config.chave_provedor)
    if preset is None:
        # "personalizado" ou chave nova — assume openai_compat se não houver outro sinal
        return ProvedorPreset(
            chave=config.chave_provedor,
            rotulo=config.chave_provedor,
            provedor="openai_compat",
            url_base=config.url_base,
            modelo_padrao=config.modelo,
            chave_padrao="",
        )
    return ProvedorPreset(
        chave=preset.chave,
        rotulo=preset.rotulo,
        provedor=preset.provedor,
        url_base=config.url_base or preset.url_base,
        modelo_padrao=config.modelo or preset.modelo_padrao,
        chave_padrao=preset.chave_padrao,
    )


# ============================================================ OpenAI-compat

def _chamar_openai_compat(
    preset: ProvedorPreset,
    config: ConfigResumo,
    texto: str,
) -> str:
    if not preset.url_base:
        raise RuntimeError(
            f"Provedor {preset.chave!r} sem URL base. Preencha o URL da API "
            "compatível com OpenAI (geralmente termina em /v1)."
        )
    if not preset.modelo_padrao:
        raise RuntimeError(
            f"Provedor {preset.chave!r} sem modelo definido. "
            "Informe o nome do modelo nas configurações."
        )

    sys_prompt, user_prompt = _montar_prompts(config, texto)
    url = preset.url_base.rstrip("/") + "/chat/completions"
    payload = {
        "model": preset.modelo_padrao,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": config.max_tokens,
        "temperature": config.temperatura,
    }
    headers = {"Content-Type": "application/json"}
    if config.chave_api:
        headers["Authorization"] = f"Bearer {config.chave_api}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    return _executar_e_extrair_texto(
        req,
        lambda dados: dados["choices"][0]["message"]["content"],
        provedor=preset.chave,
    )


# ============================================================ Anthropic

def _chamar_anthropic(
    preset: ProvedorPreset,
    config: ConfigResumo,
    texto: str,
) -> str:
    if not config.chave_api:
        raise RuntimeError(
            "O Claude (Anthropic) precisa de chave de API — cole em Configurações."
        )
    if not preset.modelo_padrao:
        raise RuntimeError(
            f"Provedor {preset.chave!r} sem modelo definido. Informe o nome do modelo."
        )

    sys_prompt, user_prompt = _montar_prompts(config, texto)
    url = preset.url_base.rstrip("/") + "/v1/messages"
    payload = {
        "model": preset.modelo_padrao,
        "max_tokens": config.max_tokens,
        "temperature": config.temperatura,
        "system": sys_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config.chave_api,
        "anthropic-version": "2023-06-01",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    return _executar_e_extrair_texto(
        req,
        lambda dados: dados["content"][0]["text"],
        provedor=preset.chave,
    )


def _executar_e_extrair_texto(req, extrair, provedor: str) -> str:
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            corpo = resp.read().decode("utf-8")
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "ignore")
        raise RuntimeError(
            f"O provedor {provedor!r} respondeu HTTP {erro.code}. "
            f"Trecho: {detalhe[:200]}"
        ) from erro
    except urllib.error.URLError as erro:
        raise RuntimeError(
            f"Não consegui falar com o provedor {provedor!r}. "
            f"Ele está rodando? Detalhe: {erro.reason}"
        ) from erro

    try:
        dados = json.loads(corpo)
    except json.JSONDecodeError as erro:
        raise RuntimeError(
            f"O provedor {provedor!r} devolveu algo que não é JSON válido: "
            f"{corpo[:200]}"
        ) from erro

    try:
        texto = extrair(dados)
    except (KeyError, IndexError, TypeError) as erro:
        raise RuntimeError(
            f"O provedor {provedor!r} devolveu um JSON sem o formato esperado: "
            f"{corpo[:200]}"
        ) from erro

    return texto.strip()


# ============================================================ ponto de entrada

def resumir(texto: str, config: ConfigResumo) -> str:
    """Manda o texto para o provedor configurado e devolve só o resumo."""
    if not texto or not texto.strip():
        raise RuntimeError("Não há texto para resumir.")

    preset = _resolver_preset(config)

    if preset.provedor == "anthropic":
        return _chamar_anthropic(preset, config, texto)
    return _chamar_openai_compat(preset, config, texto)


def provedores_disponiveis() -> list[dict]:
    """Lista serializável para o frontend (só strings e identificadores)."""
    return [
        {
            "chave": p.chave,
            "rotulo": p.rotulo,
            "provedor": p.provedor,
            "url_base_padrao": p.url_base,
            "modelo_padrao": p.modelo_padrao,
            "precisa_chave": p.chave not in {"lm_studio", "ollama", "personalizado"},
        }
        for p in PROVEDORES
    ]
