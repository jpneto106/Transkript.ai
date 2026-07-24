"""Camada de persistência em SQLite (histórico de transcrições e preferências)."""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any

from .configuracao import CAMINHO_BANCO, MODELO_PADRAO_INICIAL, garantir_pastas

# sqlite3 com check_same_thread=False + um lock nosso, já que o worker roda em outra thread.
_conexao: sqlite3.Connection | None = None
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    global _conexao
    if _conexao is None:
        garantir_pastas()
        _conexao = sqlite3.connect(CAMINHO_BANCO, check_same_thread=False)
        _conexao.row_factory = sqlite3.Row
    return _conexao


def criar_tabelas() -> None:
    with _lock:
        c = _conn()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS transcricoes (
                id                   TEXT PRIMARY KEY,
                criado_em            TEXT NOT NULL,
                atualizado_em        TEXT NOT NULL,
                entrada_original     TEXT NOT NULL,
                arquivo_local        TEXT,
                nome_arquivo         TEXT,
                modelo               TEXT NOT NULL,
                idioma_solicitado    TEXT,
                idioma_detectado     TEXT,
                probabilidade_idioma REAL,
                tarefa               TEXT NOT NULL DEFAULT 'transcribe',
                dispositivo          TEXT,
                formatos             TEXT NOT NULL,
                max_caracteres       INTEGER NOT NULL,
                max_duracao          REAL NOT NULL,
                pasta_saida          TEXT NOT NULL,
                duracao_audio        REAL,
                tempo_processamento  REAL,
                status               TEXT NOT NULL,
                progresso_segundos   REAL DEFAULT 0,
                mensagem_erro        TEXT,
                arquivos_gerados     TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_transcricoes_criado
                ON transcricoes(criado_em DESC);
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );
            """
        )
        c.commit()
        # Semear o modelo padrão inicial se ainda não houver preferência.
        cur = c.execute("SELECT valor FROM configuracoes WHERE chave = 'modelo_padrao'")
        if cur.fetchone() is None:
            c.execute(
                "INSERT INTO configuracoes (chave, valor) VALUES ('modelo_padrao', ?)",
                (MODELO_PADRAO_INICIAL,),
            )
            c.commit()


# ---------------------------------------------------------------- transcrições

_CAMPOS_JSON = {"formatos", "arquivos_gerados"}


def _linha_para_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for campo in _CAMPOS_JSON:
        if d.get(campo):
            try:
                d[campo] = json.loads(d[campo])
            except (json.JSONDecodeError, TypeError):
                d[campo] = []
        else:
            d[campo] = []
    return d


def inserir_transcricao(dados: dict[str, Any]) -> None:
    dados = dict(dados)
    for campo in _CAMPOS_JSON:
        if campo in dados and not isinstance(dados[campo], str):
            dados[campo] = json.dumps(dados[campo], ensure_ascii=False)
    colunas = ", ".join(dados.keys())
    marcadores = ", ".join(["?"] * len(dados))
    with _lock:
        c = _conn()
        c.execute(f"INSERT INTO transcricoes ({colunas}) VALUES ({marcadores})", tuple(dados.values()))
        c.commit()


def atualizar_transcricao(id_: str, campos: dict[str, Any]) -> None:
    campos = dict(campos)
    for campo in _CAMPOS_JSON:
        if campo in campos and not isinstance(campos[campo], str):
            campos[campo] = json.dumps(campos[campo], ensure_ascii=False)
    atribuicoes = ", ".join(f"{k} = ?" for k in campos)
    valores = list(campos.values()) + [id_]
    with _lock:
        c = _conn()
        c.execute(f"UPDATE transcricoes SET {atribuicoes} WHERE id = ?", valores)
        c.commit()


def obter_transcricao(id_: str) -> dict[str, Any] | None:
    with _lock:
        c = _conn()
        row = c.execute("SELECT * FROM transcricoes WHERE id = ?", (id_,)).fetchone()
    return _linha_para_dict(row) if row else None


def listar_transcricoes(limite: int = 50, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        c = _conn()
        if status:
            rows = c.execute(
                "SELECT * FROM transcricoes WHERE status = ? ORDER BY criado_em DESC LIMIT ? OFFSET ?",
                (status, limite, offset),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM transcricoes ORDER BY criado_em DESC LIMIT ? OFFSET ?",
                (limite, offset),
            ).fetchall()
    return [_linha_para_dict(r) for r in rows]


def remover_transcricao(id_: str) -> None:
    with _lock:
        c = _conn()
        c.execute("DELETE FROM transcricoes WHERE id = ?", (id_,))
        c.commit()


# --------------------------------------------------------------- configurações


def obter_config(chave: str, padrao: str | None = None) -> str | None:
    with _lock:
        c = _conn()
        row = c.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
    return row["valor"] if row else padrao


def definir_config(chave: str, valor: str) -> None:
    with _lock:
        c = _conn()
        c.execute(
            "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, valor),
        )
        c.commit()


def obter_todas_configs() -> dict[str, str]:
    with _lock:
        c = _conn()
        rows = c.execute("SELECT chave, valor FROM configuracoes").fetchall()
    return {r["chave"]: r["valor"] for r in rows}
