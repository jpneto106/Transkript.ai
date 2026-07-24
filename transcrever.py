#!/usr/bin/env python3
"""Transcritor de vídeos e áudios usando Whisper (faster-whisper).

Interface de linha de comando. Toda a lógica de transcrição vive no pacote `nucleo/`,
compartilhado com a API do aplicativo desktop.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Importar o núcleo já aplica o workaround de DLLs da NVIDIA no Windows (ver nucleo/__init__.py).
import nucleo
from nucleo import (
    FORMATOS_DISPONIVEIS,
    MODELOS_DISPONIVEIS,
    PASTA_ENTRADA_PADRAO,
    PASTA_SAIDA_PADRAO,
    EventoProgresso,
    carregar_modelo,
    detectar_dispositivo,
    encontrar_arquivos,
    escrever_saidas,
    formatar_hms,
    transcrever_arquivo,
)

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


class ProgressoRich:
    """Adaptador que liga os EventoProgresso do núcleo a uma barra do rich por arquivo."""

    def __init__(self, progress: Progress) -> None:
        self._progress = progress
        self._tarefas: dict[Path, int] = {}

    def __call__(self, evento: EventoProgresso) -> None:
        if evento.arquivo not in self._tarefas:
            total = round(evento.duracao_total, 1) if evento.duracao_total else None
            self._tarefas[evento.arquivo] = self._progress.add_task(
                f"[cyan]{evento.arquivo.name}", total=total
            )
        self._progress.update(self._tarefas[evento.arquivo], completed=evento.segundos_concluidos)


def _notificar(nivel: str, mensagem: str) -> None:
    cores = {"info": "green", "aviso": "yellow", "erro": "red"}
    rotulos = {"info": "", "aviso": "Aviso:", "erro": "Erro:"}
    cor = cores.get(nivel, "white")
    rotulo = rotulos.get(nivel, "")
    prefixo = f"[{cor}]{rotulo}[/{cor}] " if rotulo else ""
    console.print(f"{prefixo}{mensagem}")


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

    def baixar_status(mensagem: str):
        return console.status(f"[bold cyan]{mensagem}", spinner="dots")

    arquivos = encontrar_arquivos(
        entradas,
        notificar=_notificar,
        contexto_download=baixar_status,
    )
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

    dispositivo, compute_type = detectar_dispositivo(args.dispositivo, notificar=_notificar)
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
        modelo = carregar_modelo(args.modelo, dispositivo, compute_type)

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
        ao_progredir = ProgressoRich(progress)
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
                ao_progredir=ao_progredir,
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
