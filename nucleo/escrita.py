"""Gravação dos resultados da transcrição nos formatos txt/srt/vtt/json."""

from __future__ import annotations

import json
from pathlib import Path

from .formatacao import ResultadoTranscricao, formatar_timestamp_legenda


def nome_amigavel(rotulo: str | None, nomes: dict[str, str] | None = None) -> str:
    """Converte 'FALANTE_01' no nome que o usuário vê ('Falante 1' ou 'Maria')."""
    if not rotulo:
        return ""
    if nomes and rotulo in nomes:
        return nomes[rotulo]
    if rotulo.startswith("FALANTE_"):
        numero = rotulo.removeprefix("FALANTE_").lstrip("0") or "0"
        return f"Falante {numero}"
    return rotulo


def escrever_saidas(
    resultado: ResultadoTranscricao,
    pasta_saida: Path,
    formatos: list[str],
    nomes_falantes: dict[str, str] | None = None,
) -> list[Path]:
    """Grava os arquivos pedidos e devolve os caminhos gerados.

    Quando a transcrição foi diarizada, os blocos saem rotulados com o falante.
    Sem diarização, os arquivos ficam idênticos aos de sempre — há teste
    garantindo isso, porque é o caminho que a maioria dos usuários usa.
    """
    pasta_saida.mkdir(parents=True, exist_ok=True)
    base = pasta_saida / resultado.arquivo.stem
    gerados: list[Path] = []

    tem_falantes = any(seg.falante for seg in resultado.segmentos)

    def rotulo_de(seg) -> str:
        return nome_amigavel(seg.falante, nomes_falantes)

    if "txt" in formatos:
        caminho = base.with_suffix(".txt")
        if tem_falantes:
            # Agrupa falas seguidas da mesma pessoa num parágrafo só, com linha
            # em branco na troca de voz — assim o diálogo fica legível.
            linhas: list[str] = []
            falante_anterior: str | None = None
            for seg in resultado.segmentos:
                if seg.falante != falante_anterior:
                    if falante_anterior is not None:
                        linhas.append("")
                    linhas.append(f"{rotulo_de(seg)}: {seg.texto.strip()}")
                    falante_anterior = seg.falante
                else:
                    linhas.append(seg.texto.strip())
        else:
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
            texto = seg.texto.strip()
            linhas.append(f"{rotulo_de(seg)}: {texto}" if seg.falante else texto)
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
            texto = seg.texto.strip()
            # <v Nome> é a marcação padrão do WebVTT para identificar quem fala:
            # players que a entendem mostram o nome; os demais ignoram a tag.
            linhas.append(f"<v {rotulo_de(seg)}>{texto}" if seg.falante else texto)
            linhas.append("")
        caminho.write_text("\n".join(linhas), encoding="utf-8")
        gerados.append(caminho)

    if "json" in formatos:
        caminho = base.with_suffix(".json")
        segmentos = []
        for s in resultado.segmentos:
            item = {"inicio": s.inicio, "fim": s.fim, "texto": s.texto.strip()}
            if s.falante:
                item["falante"] = s.falante
            segmentos.append(item)

        dados = {
            "arquivo": str(resultado.arquivo),
            "idioma": resultado.idioma,
            "probabilidade_idioma": resultado.probabilidade_idioma,
            "duracao_segundos": resultado.duracao,
            "segmentos": segmentos,
        }
        if tem_falantes:
            dados["falantes"] = {
                rotulo: nome_amigavel(rotulo, nomes_falantes) for rotulo in resultado.falantes
            }
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        gerados.append(caminho)

    return gerados
