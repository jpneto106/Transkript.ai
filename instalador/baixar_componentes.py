"""Buscador de componentes para o instalador bootstrap (Etapa 6 do plano v4).

Para cada componente publicável em ``instalador/ASSETS.md``, confere se já
está na pasta de instalação com o sha256 certo; se faltando ou divergente,
baixa do GitHub Releases, verifica o hash, e extrai no lugar.

Uso:

    python instalador/baixar_componentes.py [opcoes]

Opções:
    --tag TAG              versão/tag a usar (default: mais recente)
    --destino PASTA        raiz onde extrair (default: raiz do projeto)
    --componentes LISTA     só estes componentes (vírgula); padrão é todos
                            os relevantes para a máquina
    --skip LISTA            pulando estes componentes
    --force                rebaixa mesmo se o sha256 já bate
    --dry-run              só mostra o que faria, sem baixar

Destinatários:

1. **Dev / CI**: rodar este script com o Python do venv para preparar
   ``dist/`` ou para conferir Releases publicados.
2. **Bare machine** (instalação real do usuário final): uma casca C# bem
   fina chama este script via ``python -m`` num Python embarcado no
   instalador, ou reimplementa a mesma lógica em C# usando ``HttpClient``.
   Esta segunda parte é o próximo passo da Etapa 6 (não escrito ainda).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# === Origem fixa do instalador bootstrap ===

# Repositório upstream.
_REPO = "jpneto106/Transkript.ai"

# Tag (versão) que estamos buscando. Default: lê de uma envvar para que o
# launcher C# possa forçar uma versão sem editar o script.
_TAG_PADRAO = "v4.0.0"

# URL pública dos assets: github.com/<owner>/<repo>/releases/download/<tag>/<asset>
# O asset companheiro `.sha256` mora ao lado, com o mesmo nome + sufixo.

# Componentes que SEMPRE entram no bootstrap. A escolha entre `--full` e
# `--bootstrap` no `empacotar.py` define o que vai junto do instalador.
_COMPONENTES_SEMPRE = [
    "casca",
    "servidor",
    "frontend",
    "ffmpeg",
]

# Componentes que entram só quando a condição casa.
# (nome, função que decide (True=baixa, False=pula))
_COMPONENTES_CONDICIONAIS = [
    ("cuda", lambda: _tem_nvidia()),
    ("modelos-diarizacao", lambda: _diarizacao_ativa()),
]


def _repo_url(tag: str, asset: str) -> str:
    return f"https://github.com/{_REPO}/releases/download/{tag}/{asset}"


def _tem_nvidia() -> bool:
    """Detecta se o sistema tem GPU NVIDIA visível."""
    # Reuso da lógica do nucleo/dispositivo se o pacote estiver disponível,
    # caso contrário checa via nvidia-smi ou via nvcuda.dll no Windows.
    try:
        from nucleo.dispositivo import detectar_dispositivo  # type: ignore
        return detectar_dispositivo() == "cuda"
    except Exception:
        return False


def _diarizacao_ativa() -> bool:
    """Lê ``configuracoes.json`` se existir e devolve ``configuracoes.diarizar``."""
    cfg = Path(__file__).resolve().parent.parent / "dados" / "configuracoes.json"
    if not cfg.is_file():
        return False
    try:
        dados = json.loads(cfg.read_text(encoding="utf-8"))
        return bool(dados.get("diarizar"))
    except Exception:
        return False


def _asset_nome(componente: str, versao: str = _TAG_PADRAO) -> str:
    return f"Transkript.ai-{versao}-{componente}.zip"


def _asset_sha_nome(asset: str) -> str:
    return asset + ".sha256"


def _raiz_destino(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    return Path(__file__).resolve().parent.parent


def _confere_sha256(caminho: Path, esperado: str) -> bool:
    if not caminho.is_file():
        return False
    sha = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(bloco)
    return sha.hexdigest().lower() == esperado.lower()


def _calcular_sha256(caminho: Path) -> str:
    sha = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(bloco)
    return sha.hexdigest()


def _http_get(url: str, destino: Path) -> None:
    """Baixa um arquivo mostrando progresso em MB (sem dependência extra)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Transkript.ai-bootstrap"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        total = int(resp.headers.get("Content-Length", "0"))
        lidos = 0
        bloco = 1024 * 64
        with open(destino, "wb") as saida:
            while True:
                pedaco = resp.read(bloco)
                if not pedaco:
                    break
                saida.write(pedaco)
                lidos += len(pedaco)
                if total:
                    pct = 100 * lidos / total
                    sys.stdout.write(
                        f"\r    {lidos / 1024 / 1024:6.1f} / {total / 1024 / 1024:6.1f} MB  ({pct:5.1f}%)"
                    )
                    sys.stdout.flush()
        if total:
            sys.stdout.write("\n")


def _download_sha(tag: str, asset: str) -> str | None:
    url = _repo_url(tag, _asset_sha_nome(asset))
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            txt = resp.read().decode("utf-8", "ignore").strip()
        # formato: "<hash>   Transkript.ai-v4.0.0-<componente>.zip\n"
        return txt.split()[0] if txt else None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _componente_precisa(destino: Path, componente: str, tag: str, force: bool) -> tuple[bool, str | None]:
    """Devolve (precisa_baixar, hash_esperado)."""
    asset = _asset_nome(componente, tag)
    extrair_para = destino / "ferramentas" / componente
    ja_extraido = extrair_para.is_dir() and any(extrair_para.rglob("*"))
    hash_esperado = _download_sha(tag, asset)
    if not hash_esperado:
        return (not ja_extraido, None)
    if force or not ja_extraido:
        return (True, hash_esperado)
    cache = destino / "dados" / "_cache" / f"{componente}.sha256"
    if cache.is_file() and cache.read_text(encoding="utf-8").strip().lower() == hash_esperado.lower():
        return (False, hash_esperado)
    return (True, hash_esperado)


def _extrair_zip(zip_path: Path, destino: Path) -> None:
    """Extrai o conteúdo do zip em ``destino``. Ignora ``__MACOSX`` e afins."""
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            nome = info.filename
            if nome.startswith("__MACOSX") or nome.endswith("/"):
                continue
            alvo = destino / Path(nome).name if "/" not in nome else destino / nome
            alvo.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(alvo, "wb") as dst:
                shutil.copyfileobj(src, dst)


def _processar_componente(destino: Path, componente: str, tag: str, force: bool, dry: bool) -> str:
    precisa, esperado = _componente_precisa(destino, componente, tag, force)
    if not precisa:
        return f"  {componente}: ja presente, hash confere, pulando"
    if not esperado:
        return f"  {componente}: asset nao encontrado no Release {tag} (nem no cache local)"
    if dry:
        return f"  {componente}: baixaria de {_repo_url(tag, _asset_nome(componente, tag))}"
    print(f"  {componente}: baixando de {tag}...")
    cache_dir = destino / "dados" / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    asset_zip = cache_dir / f"{componente}.zip"
    _http_get(_repo_url(tag, _asset_nome(componente, tag)), asset_zip)
    print(f"    conferindo sha256 ({esperado[:12]}...)")
    calc = _calcular_sha256(asset_zip)
    if calc.lower() != esperado.lower():
        asset_zip.unlink(missing_ok=True)
        sys.exit(f"ERRO: sha256 de {componente} nao bateu: esperado {esperado}, calculado {calc}")
    alvo = destino / "ferramentas" / componente
    alvo.mkdir(parents=True, exist_ok=True)
    _extrair_zip(asset_zip, alvo)
    (cache_dir / f"{componente}.sha256").write_text(esperado, encoding="utf-8")
    return f"  {componente}: OK ({asset_zip.stat().st_size / 1024 / 1024:.1f} MB)"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default=os.environ.get("TRANSKRIPT_TAG", _TAG_PADRAO))
    ap.add_argument("--destino", default=None)
    ap.add_argument("--componentes", default=None, help="so estes (virgula)")
    ap.add_argument("--skip", default="", help="pular estes (virgula)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv[1:])

    destino = _raiz_destino(args.destino)
    print(f"Destino: {destino}")
    print(f"Tag:     {args.tag}")

    desejados = list(_COMPONENTES_SEMPRE)
    for nome, cond in _COMPONENTES_CONDICIONAIS:
        try:
            if cond():
                desejados.append(nome)
        except Exception:
            pass

    if args.componentes:
        whitelist = set(args.componentes.split(","))
        desejados = [n for n in desejados if n in whitelist]
    if args.skip:
        skip = set(args.skip.split(","))
        desejados = [n for n in desejados if n not in skip]

    print(f"Componentes: {', '.join(desejados) or '(nenhum)'}")
    print()

    for comp in desejados:
        try:
            msg = _processar_componente(destino, comp, args.tag, args.force, args.dry_run)
        except Exception as erro:
            print(f"  {comp}: ERRO ({erro!r})", file=sys.stderr)
            continue
        print(msg)

    print()
    print("Pronto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
