"""Testes da identificação de falantes nos blocos e nas saídas.

O ponto mais importante aqui é o teste de regressão: sem diarização, os arquivos
gerados têm de continuar exatamente como sempre foram — é o caminho que a
maioria dos usuários usa, e não pode mudar por causa de um recurso opcional.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nucleo.blocos import montar_blocos
from nucleo.escrita import escrever_saidas, nome_amigavel
from nucleo.formatacao import Palavra, ResultadoTranscricao, Segmento


def _palavra(inicio, fim, texto, falante=None):
    return Palavra(inicio=inicio, fim=fim, texto=texto, falante=falante)


# --------------------------------------------------------------- montar_blocos

def test_troca_de_falante_fecha_o_bloco():
    """Mesmo cabendo no limite, vozes diferentes não podem dividir um bloco."""
    palavras = [
        _palavra(0.0, 0.5, " Oi", "FALANTE_01"),
        _palavra(0.5, 1.0, " tudo", "FALANTE_01"),
        _palavra(1.0, 1.5, " bem", "FALANTE_02"),
        _palavra(1.5, 2.0, " sim", "FALANTE_02"),
    ]
    blocos = montar_blocos(palavras, max_caracteres=200, max_duracao=60)
    assert len(blocos) == 2
    assert blocos[0].texto == "Oi tudo" and blocos[0].falante == "FALANTE_01"
    assert blocos[1].texto == "bem sim" and blocos[1].falante == "FALANTE_02"


def test_sem_falante_agrupa_como_antes():
    palavras = [_palavra(0.0, 0.5, " Oi"), _palavra(0.5, 1.0, " tudo")]
    blocos = montar_blocos(palavras, max_caracteres=200, max_duracao=60)
    assert len(blocos) == 1
    assert blocos[0].falante is None


def test_limite_de_caracteres_continua_valendo_dentro_do_mesmo_falante():
    palavras = [_palavra(i * 0.5, i * 0.5 + 0.5, " palavra", "FALANTE_01") for i in range(6)]
    blocos = montar_blocos(palavras, max_caracteres=20, max_duracao=60)
    assert len(blocos) > 1
    assert all(b.falante == "FALANTE_01" for b in blocos)


# ----------------------------------------------------------------- rótulo amigável

def test_rotulo_padrao_e_numero_legivel():
    assert nome_amigavel("FALANTE_01") == "Falante 1"
    assert nome_amigavel("FALANTE_12") == "Falante 12"
    assert nome_amigavel(None) == ""


def test_nome_personalizado_tem_prioridade():
    assert nome_amigavel("FALANTE_01", {"FALANTE_01": "Maria"}) == "Maria"


# ------------------------------------------------------------------- escrita

def _resultado_com_falantes(tmp_path):
    return ResultadoTranscricao(
        arquivo=tmp_path / "entrevista.mp4",
        idioma="pt",
        probabilidade_idioma=0.99,
        duracao=6.0,
        segmentos=[
            Segmento(0.0, 2.0, "Bom dia.", falante="FALANTE_01"),
            Segmento(2.0, 4.0, "Como vai?", falante="FALANTE_01"),
            Segmento(4.0, 6.0, "Tudo bem.", falante="FALANTE_02"),
        ],
        falantes=["FALANTE_01", "FALANTE_02"],
    )


def test_txt_agrupa_falas_seguidas_do_mesmo_falante(tmp_path):
    gerados = escrever_saidas(_resultado_com_falantes(tmp_path), tmp_path / "out", ["txt"])
    conteudo = gerados[0].read_text(encoding="utf-8")
    assert conteudo == "Falante 1: Bom dia.\nComo vai?\n\nFalante 2: Tudo bem.\n"


def test_srt_prefixa_o_nome_do_falante(tmp_path):
    gerados = escrever_saidas(_resultado_com_falantes(tmp_path), tmp_path / "out", ["srt"])
    conteudo = gerados[0].read_text(encoding="utf-8")
    assert "Falante 1: Bom dia." in conteudo
    assert "Falante 2: Tudo bem." in conteudo


def test_vtt_usa_a_marcacao_de_voz(tmp_path):
    gerados = escrever_saidas(_resultado_com_falantes(tmp_path), tmp_path / "out", ["vtt"])
    conteudo = gerados[0].read_text(encoding="utf-8")
    assert "<v Falante 1>Bom dia." in conteudo


def test_json_traz_falante_por_segmento_e_o_mapa(tmp_path):
    gerados = escrever_saidas(_resultado_com_falantes(tmp_path), tmp_path / "out", ["json"])
    dados = json.loads(gerados[0].read_text(encoding="utf-8"))
    assert dados["segmentos"][0]["falante"] == "FALANTE_01"
    assert dados["falantes"] == {"FALANTE_01": "Falante 1", "FALANTE_02": "Falante 2"}


def test_nomes_personalizados_aparecem_nas_saidas(tmp_path):
    gerados = escrever_saidas(
        _resultado_com_falantes(tmp_path), tmp_path / "out", ["txt", "json"],
        nomes_falantes={"FALANTE_01": "Ana", "FALANTE_02": "Bruno"},
    )
    txt = [g for g in gerados if g.suffix == ".txt"][0].read_text(encoding="utf-8")
    assert txt.startswith("Ana: Bom dia.")
    dados = json.loads([g for g in gerados if g.suffix == ".json"][0].read_text(encoding="utf-8"))
    assert dados["falantes"]["FALANTE_02"] == "Bruno"


# ------------------------------------------------------- regressão (sem diarização)

def test_sem_diarizacao_as_saidas_nao_mudam(tmp_path):
    """Guarda-chuva do caminho normal: nada de rótulos, nada de chave extra."""
    resultado = ResultadoTranscricao(
        arquivo=tmp_path / "aula.mp4",
        idioma="pt",
        probabilidade_idioma=0.98,
        duracao=4.0,
        segmentos=[Segmento(0.0, 2.0, "Primeira."), Segmento(2.0, 4.0, "Segunda.")],
    )
    gerados = escrever_saidas(resultado, tmp_path / "out", ["txt", "srt", "vtt", "json"])
    por_tipo = {g.suffix: g.read_text(encoding="utf-8") for g in gerados}

    assert por_tipo[".txt"] == "Primeira.\nSegunda.\n"
    assert ":" not in por_tipo[".srt"].split("-->")[1].split("\n")[1]  # sem "Nome:"
    assert "<v " not in por_tipo[".vtt"]
    dados = json.loads(por_tipo[".json"])
    assert "falantes" not in dados
    assert "falante" not in dados["segmentos"][0]
