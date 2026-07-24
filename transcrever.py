#!/usr/bin/env python3
"""Transcritor de vídeos e áudios usando Whisper (faster-whisper)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


def _registrar_dlls_nvidia() -> None:
    """No Windows, as DLLs de cuBLAS/cuDNN instaladas via pip (nvidia-*-cu12) ficam
    dentro de site-packages e o ctranslate2 só as encontra se estiverem no PATH
    (os.add_dll_directory não é suficiente para os LoadLibrary internos dele)."""
    if os.name != "nt":
        return
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not base.is_dir():
        return
    pastas = [str(p) for p in base.glob("*/bin")]
    if pastas:
        os.environ["PATH"] = os.pathsep.join(pastas) + os.pathsep + os.environ.get("PATH", "")


_registrar_dlls_nvidia()

if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich import box

console = Console()

EXTENSOES_SUPORTADAS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".opus",
}

MODELOS_DISPONIVEIS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
FORMATOS_DISPONIVEIS = ["txt", "srt", "vtt", "json"]

PASTA_ENTRADA_PADRAO = Path("entrada")
PASTA_SAIDA_PADRAO = "saida"
PASTA_DOWNLOADS = PASTA_ENTRADA_PADRAO / "_downloads"

FINALIZADORES_DE_FRASE = (".", "!", "?", "…")


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
        blocos.append(Segmento(inicio=atual[0].inicio, fim=atual[-1].fim, texto=texto_de(atual)))
        atual.clear()

    for palavra in palavras:
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


def detectar_dispositivo(preferencia: str) -> tuple[str, str]:
    """Decide device/compute_type para o ctranslate2, respeitando preferência do usuário."""
    if preferencia == "cpu":
        return "cpu", "int8"

    dispositivo = "cpu"
    if preferencia in ("auto", "cuda"):
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                dispositivo = "cuda"
        except Exception:
            dispositivo = "cpu"

    if preferencia == "cuda" and dispositivo != "cuda":
        console.print(
            "[yellow]Aviso:[/yellow] GPU CUDA não encontrada, usando CPU.",
        )

    compute_type = "float16" if dispositivo == "cuda" else "int8"
    return dispositivo, compute_type


def eh_url(texto: str) -> bool:
    return texto.startswith("http://") or texto.startswith("https://")


def baixar_de_url(url: str, pasta_destino: Path) -> Path:
    import yt_dlp

    pasta_destino.mkdir(parents=True, exist_ok=True)
    opcoes = {
        "format": "bestaudio/best",
        "outtmpl": str(pasta_destino / "%(title).150B [%(id)s].%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "restrictfilenames": False,
    }
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info))


def encontrar_arquivos(entradas: list[str]) -> list[Path]:
    arquivos: list[Path] = []
    for entrada in entradas:
        if eh_url(entrada):
            with console.status(f"[bold cyan]Baixando vídeo de: {entrada}", spinner="dots"):
                try:
                    caminho = baixar_de_url(entrada, PASTA_DOWNLOADS)
                except Exception as erro:
                    console.print(f"[red]Erro ao baixar '{entrada}':[/red] {erro}")
                    continue
            console.print(f"[green]Baixado:[/green] {caminho.name}")
            arquivos.append(caminho)
            continue

        caminho = Path(entrada)
        if caminho.is_dir():
            for item in sorted(caminho.rglob("*")):
                if item.is_file() and item.suffix.lower() in EXTENSOES_SUPORTADAS:
                    arquivos.append(item)
        elif caminho.is_file():
            arquivos.append(caminho)
        else:
            console.print(f"[red]Aviso:[/red] '{entrada}' não encontrado, ignorando.")
    return arquivos


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


def transcrever_arquivo(
    modelo,
    arquivo: Path,
    idioma: str | None,
    tarefa: str,
    beam_size: int,
    vad_filter: bool,
    max_caracteres: int,
    max_duracao: float,
    progress: Progress,
) -> ResultadoTranscricao:
    segmentos_gerados, info = modelo.transcribe(
        str(arquivo),
        language=idioma,
        task=tarefa,
        beam_size=beam_size,
        vad_filter=vad_filter,
        word_timestamps=True,
    )

    duracao = info.duration
    tarefa_progresso = progress.add_task(
        f"[cyan]{arquivo.name}", total=round(duracao, 1) if duracao else None
    )

    resultado = ResultadoTranscricao(
        arquivo=arquivo,
        idioma=info.language,
        probabilidade_idioma=info.language_probability,
        duracao=duracao,
    )

    segmentos_brutos = []
    inicio_processamento = time.perf_counter()
    for seg in segmentos_gerados:
        segmentos_brutos.append(seg)
        progress.update(tarefa_progresso, completed=min(seg.end, duracao) if duracao else seg.end)
    progress.update(tarefa_progresso, completed=duracao)
    resultado.tempo_processamento = time.perf_counter() - inicio_processamento

    palavras = extrair_palavras(segmentos_brutos)
    resultado.segmentos = montar_blocos(palavras, max_caracteres=max_caracteres, max_duracao=max_duracao)

    return resultado


def montar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcreve vídeos e áudios usando Whisper (faster-whisper), localmente.",
    )
    parser.add_argument(
        "entradas", nargs="*",
        help=(
            "Arquivo(s) de vídeo/áudio, pasta(s) ou link(s) (http/https, ex: YouTube). "
            f"Se omitido, processa tudo que estiver na pasta '{PASTA_ENTRADA_PADRAO}/'."
        ),
    )
    parser.add_argument(
        "--modelo", "-m", default="medium", choices=MODELOS_DISPONIVEIS,
        help="Tamanho do modelo Whisper (padrão: medium).",
    )
    parser.add_argument(
        "--idioma", "-l", default=None,
        help="Código do idioma (ex: pt, en). Se omitido, detecta automaticamente.",
    )
    parser.add_argument(
        "--tarefa", choices=["transcribe", "translate"], default="transcribe",
        help="'transcribe' mantém o idioma original, 'translate' traduz para inglês.",
    )
    parser.add_argument(
        "--dispositivo", "-d", choices=["auto", "cpu", "cuda"], default="auto",
        help="Dispositivo de processamento (padrão: auto detecta GPU).",
    )
    parser.add_argument(
        "--saida", "-o", default=PASTA_SAIDA_PADRAO,
        help=f"Pasta onde salvar os resultados (padrão: ./{PASTA_SAIDA_PADRAO}).",
    )
    parser.add_argument(
        "--formatos", "-f", nargs="+", default=["txt", "srt"], choices=FORMATOS_DISPONIVEIS,
        help="Formatos de saída desejados (padrão: txt srt).",
    )
    parser.add_argument(
        "--beam-size", type=int, default=5, help="Beam size da decodificação (padrão: 5).",
    )
    parser.add_argument(
        "--sem-vad", action="store_true",
        help="Desativa o filtro de detecção de voz (VAD), que por padrão pula trechos de silêncio.",
    )
    parser.add_argument(
        "--max-caracteres", type=int, default=80,
        help="Máximo de caracteres por bloco de transcrição/legenda (padrão: 80).",
    )
    parser.add_argument(
        "--max-duracao", type=float, default=6.0,
        help="Duração máxima (segundos) de cada bloco de transcrição/legenda (padrão: 6.0).",
    )
    return parser.parse_args()


def main() -> None:
    args = montar_argumentos()

    console.print(
        Panel.fit(
            "[bold]Transcritor de Vídeos[/bold]\n[dim]Whisper local via faster-whisper[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    usando_pasta_padrao = not args.entradas
    if usando_pasta_padrao:
        PASTA_ENTRADA_PADRAO.mkdir(exist_ok=True)
        entradas = [str(PASTA_ENTRADA_PADRAO)]
    else:
        entradas = args.entradas

    arquivos = encontrar_arquivos(entradas)
    if not arquivos:
        if usando_pasta_padrao:
            console.print(
                f"[bold red]Nenhum arquivo encontrado na pasta '{PASTA_ENTRADA_PADRAO.resolve()}'.[/bold red]\n"
                "[yellow]Coloque seus vídeos/áudios ali e rode o script de novo, ou informe o caminho/link "
                "diretamente:[/yellow] python transcrever.py \"caminho\\do\\video.mp4\""
            )
        else:
            console.print("[bold red]Nenhum arquivo de vídeo/áudio válido encontrado.[/bold red]")
        sys.exit(1)

    dispositivo, compute_type = detectar_dispositivo(args.dispositivo)
    pasta_saida = Path(args.saida)

    tabela_config = Table(box=box.SIMPLE, show_header=False)
    tabela_config.add_row("Pasta de entrada", str(PASTA_ENTRADA_PADRAO.resolve()) if usando_pasta_padrao else "(arquivos informados na linha de comando)")
    tabela_config.add_row("Pasta de saída", str(pasta_saida.resolve()))
    tabela_config.add_row("Modelo", args.modelo)
    tabela_config.add_row("Dispositivo", f"{dispositivo} ({compute_type})")
    tabela_config.add_row("Idioma", args.idioma or "detecção automática")
    tabela_config.add_row("Formatos de saída", ", ".join(args.formatos))
    tabela_config.add_row("Máx. por bloco", f"{args.max_caracteres} caracteres / {args.max_duracao:.0f}s")
    tabela_config.add_row("Arquivos encontrados", str(len(arquivos)))
    console.print(tabela_config)

    with console.status(f"[bold cyan]Carregando modelo '{args.modelo}'...", spinner="dots"):
        from faster_whisper import WhisperModel

        modelo = WhisperModel(args.modelo, device=dispositivo, compute_type=compute_type)

    console.print("[green]Modelo carregado.[/green]\n")

    resumo = Table(title="Resumo da transcrição", box=box.ROUNDED, show_lines=False)
    resumo.add_column("Arquivo", style="cyan", overflow="fold")
    resumo.add_column("Idioma")
    resumo.add_column("Duração", justify="right")
    resumo.add_column("Tempo de processamento", justify="right")
    resumo.add_column("Saída", overflow="fold")

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed:.0f}s / {task.total:.0f}s"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        for arquivo in arquivos:
            resultado = transcrever_arquivo(
                modelo,
                arquivo,
                idioma=args.idioma,
                tarefa=args.tarefa,
                beam_size=args.beam_size,
                vad_filter=not args.sem_vad,
                max_caracteres=args.max_caracteres,
                max_duracao=args.max_duracao,
                progress=progress,
            )
            gerados = escrever_saidas(resultado, pasta_saida, args.formatos)
            resumo.add_row(
                resultado.arquivo.name,
                f"{resultado.idioma} ({resultado.probabilidade_idioma:.0%})",
                formatar_hms(resultado.duracao),
                formatar_hms(resultado.tempo_processamento),
                "\n".join(str(g) for g in gerados),
            )

    console.print()
    console.print(resumo)
    console.print(f"\n[bold green]Concluído![/bold green] Resultados salvos em [cyan]{pasta_saida.resolve()}[/cyan]")


if __name__ == "__main__":
    main()
