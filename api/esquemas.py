"""Modelos Pydantic de requisição/resposta da API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from nucleo.constantes import FORMATOS_DISPONIVEIS, MODELOS_DISPONIVEIS


class CriarTranscricaoRequest(BaseModel):
    entrada: str = Field(..., description="Caminho de arquivo local ou URL (http/https).")
    modelo: str = Field("small", description="Modelo Whisper.")
    idioma: str | None = Field(None, description="Código do idioma (ex: pt). None = detectar.")
    tarefa: str = Field("transcribe", description="'transcribe' ou 'translate'.")
    dispositivo: str = Field("auto", description="'auto', 'cpu' ou 'cuda'.")
    formatos: list[str] = Field(default_factory=lambda: ["txt", "srt"])
    max_caracteres: int = Field(80, ge=10, le=500)
    max_duracao: float = Field(6.0, gt=0, le=60)
    beam_size: int = Field(5, ge=1, le=10)
    vad_filter: bool = Field(True, description="Pular trechos de silêncio.")
    dicionario_id: str | None = Field(None, description="Dicionário de termos a usar (initial_prompt).")
    diarizar: bool = Field(False, description="Identificar quem fala em cada trecho.")
    num_falantes: int | None = Field(
        None, ge=1, le=20,
        description="Quantidade de falantes, se conhecida. None = detectar automaticamente.",
    )


class InfoMidiaRequest(BaseModel):
    caminho: str = Field(..., description="Caminho local do arquivo de áudio/vídeo.")


class DicionarioRequest(BaseModel):
    nome: str = Field(..., min_length=1)
    descricao: str | None = None
    termos: list[str] = Field(default_factory=list)


class CriarTranscricaoResposta(BaseModel):
    id: str
    status: str


class AtualizarConfigRequest(BaseModel):
    """Campos do PUT /api/config.

    Cada atributo é opcional — o front envia só os que o usuário mexeu. O
    backend persiste cada um via ``bd.definir_config`` (key-value em SQLite).
    """

    modelo_padrao: str | None = Field(
        None,
        description="Modelo Whisper/Parakeet selecionado por padrão em novas transcrições.",
    )
    idioma_padrao: str | None = Field(
        None,
        description='Código BCP-47 (pt, en, es, …) ou "auto" para detecção.',
    )
    formatos_padrao: list[str] | None = Field(
        None, description='Lista de formatos a gerar por padrão (["txt","srt",…]).',
    )
    preset_blocos: str | None = Field(
        None, description="preset de tamanho do nucleo/blocos.py (padrao/longo/curto/reel/frase).",
    )
    diarizar_por_padrao: bool | None = Field(
        None, description="Marcar 'identificar falantes' por padrão.",
    )
    # Resumo por IA (campos achatados; o prefixo "resumo_" distingue do resto)
    resumo_ativo: bool | None = Field(
        None, description="Liga/desliga o recurso de resumo por IA. Por padrão desligado.",
    )
    resumo_provedor: str | None = Field(
        None, description="Identificador do provedor (lm_studio, ollama, groq, claude, …).",
    )
    resumo_chave_api: str | None = Field(
        None, description="Chave do provedor. Nunca fica em texto puro dentro do bundle.",
    )
    resumo_modelo: str | None = Field(
        None, description="Nome do modelo no provedor.",
    )
    resumo_estilo: str | None = Field(
        None, description="curto / topicos / frases_chave / executivo",
    )
    resumo_max_tokens: int | None = Field(
        None, ge=128, le=8192, description="Teto de tokens da resposta do modelo.",
    )


class OpcoesResposta(BaseModel):
    modelos: list[str] = MODELOS_DISPONIVEIS
    formatos: list[str] = FORMATOS_DISPONIVEIS
