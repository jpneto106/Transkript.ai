"""Consulta e gerência do cache local de modelos faster-whisper (via huggingface_hub)."""

from __future__ import annotations

from nucleo.constantes import MODELOS_DISPONIVEIS

# Metadados amigáveis por modelo, para a interface explicar o trade-off ao usuário.
# tamanho_aprox_mb é só uma referência de download; o tamanho real em disco vem do cache.
INFO_MODELOS = {
    "tiny":     {"rotulo": "Tiny",      "resumo": "Muito rápido, qualidade básica",        "tamanho_aprox_mb": 75,   "recomendado": False},
    "base":     {"rotulo": "Base",      "resumo": "Rápido, qualidade razoável",             "tamanho_aprox_mb": 145,  "recomendado": False},
    "small":    {"rotulo": "Small",     "resumo": "Rápido e boa qualidade (recomendado)",   "tamanho_aprox_mb": 480,  "recomendado": True},
    "medium":   {"rotulo": "Medium",    "resumo": "Mais lento, ótima qualidade",            "tamanho_aprox_mb": 1500, "recomendado": False},
    "large-v2": {"rotulo": "Large v2",  "resumo": "Lento, qualidade máxima",                "tamanho_aprox_mb": 3000, "recomendado": False},
    "large-v3": {"rotulo": "Large v3",  "resumo": "Lento, a melhor qualidade",              "tamanho_aprox_mb": 3000, "recomendado": False},
}


def _repo_id(nome: str) -> str:
    return f"Systran/faster-whisper-{nome}"


def _mapa_tamanho_em_disco() -> dict[str, int]:
    """Retorna {nome_modelo: bytes_em_disco} para os modelos já baixados."""
    try:
        from huggingface_hub import scan_cache_dir

        info = scan_cache_dir()
    except Exception:
        return {}

    tamanhos: dict[str, int] = {}
    for repo in info.repos:
        for nome in MODELOS_DISPONIVEIS:
            if repo.repo_id == _repo_id(nome):
                tamanhos[nome] = repo.size_on_disk
    return tamanhos


def listar_modelos(modelo_padrao: str | None) -> list[dict]:
    tamanhos = _mapa_tamanho_em_disco()
    resultado = []
    for nome in MODELOS_DISPONIVEIS:
        info = INFO_MODELOS.get(nome, {})
        bytes_disco = tamanhos.get(nome)
        resultado.append(
            {
                "nome": nome,
                "rotulo": info.get("rotulo", nome),
                "resumo": info.get("resumo", ""),
                "recomendado": info.get("recomendado", False),
                "tamanho_aprox_mb": info.get("tamanho_aprox_mb"),
                "baixado": bytes_disco is not None,
                "tamanho_disco_mb": round(bytes_disco / (1024 * 1024), 1) if bytes_disco else None,
                "e_padrao": nome == modelo_padrao,
            }
        )
    return resultado


def baixar_modelo(nome: str) -> None:
    """Baixa os arquivos do modelo para o cache local (sem carregar na GPU/CPU)."""
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=_repo_id(nome))


def remover_modelo(nome: str) -> bool:
    """Remove o modelo do cache local. Retorna True se algo foi removido."""
    from huggingface_hub import scan_cache_dir

    info = scan_cache_dir()
    hashes = []
    for repo in info.repos:
        if repo.repo_id == _repo_id(nome):
            hashes.extend(rev.commit_hash for rev in repo.revisions)
    if not hashes:
        return False
    info.delete_revisions(*hashes).execute()
    return True
