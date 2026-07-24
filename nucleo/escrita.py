"""Gravação dos resultados da transcrição nos formatos txt/srt/vtt/json."""

from __future__ import annotations

import json
from pathlib import Path

from .formatacao import ResultadoTranscricao, formatar_timestamp_legenda


def escrever_saidas(resultado: ResultadoTranscricao, pasta_saida: Path, formatos: list[str]) -> list[Path]:
    pasta_saida.mkdir(parents=True, exist_ok=True)
    base = pasta_saida / resultado.arquivo.stem
    gerados: list[Path] = []

    if "txt" in formatos:
        caminho = base.with_suffix(".txt")
        linhas = [seg.texto.strip() for seg in resultado.segmentos]
        caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        gerados.append(caminho)

    if "srt" in formatos:
        caminho = base.with_suffix(".srt")
        linhas = []
        for i, seg in enumerate(resultado.segmentos, start=1):
            linhas.append(str(i))
            linhas.append(
                f"{formatar_timestamp_legenda(seg.inicio)} --> {formatar_timestamp_legenda(seg.fim)}"
            )
            linhas.append(seg.texto.strip())
            linhas.append("")
        caminho.write_text("\n".join(linhas), encoding="utf-8")
        gerados.append(caminho)

    if "vtt" in formatos:
        caminho = base.with_suffix(".vtt")
        linhas = ["WEBVTT", ""]
        for seg in resultado.segmentos:
            linhas.append(
                f"{formatar_timestamp_legenda(seg.inicio, '.')} --> {formatar_timestamp_legenda(seg.fim, '.')}"
            )
            linhas.append(seg.texto.strip())
            linhas.append("")
        caminho.write_text("\n".join(linhas), encoding="utf-8")
        gerados.append(caminho)

    if "json" in formatos:
        caminho = base.with_suffix(".json")
        dados = {
            "arquivo": str(resultado.arquivo),
            "idioma": resultado.idioma,
            "probabilidade_idioma": resultado.probabilidade_idioma,
            "duracao_segundos": resultado.duracao,
            "segmentos": [
                {"inicio": s.inicio, "fim": s.fim, "texto": s.texto.strip()}
                for s in resultado.segmentos
            ],
        }
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        gerados.append(caminho)

    return gerados
