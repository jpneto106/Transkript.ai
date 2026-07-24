"""Estruturas de dados da transcrição e funções de formatação de tempo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segmento:
    inicio: float
    fim: float
    texto: str


@dataclass
class Palavra:
    inicio: float
    fim: float
    texto: str


@dataclass
class ResultadoTranscricao:
    arquivo: Path
    idioma: str
    probabilidade_idioma: float
    duracao: float
    segmentos: list[Segmento] = field(default_factory=list)
    tempo_processamento: float = 0.0

    @property
    def texto_completo(self) -> str:
        return " ".join(s.texto.strip() for s in self.segmentos).strip()


def formatar_hms(segundos: float) -> str:
    segundos = max(0.0, segundos)
    horas, resto = divmod(int(segundos), 3600)
    minutos, segs = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segs:02d}"


def formatar_timestamp_legenda(segundos: float, separador_ms: str = ",") -> str:
    segundos = max(0.0, segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, resto = divmod(resto, 60)
    segs, ms = divmod(resto, 1)
    return f"{int(horas):02d}:{int(minutos):02d}:{int(segs):02d}{separador_ms}{int(ms * 1000):03d}"
