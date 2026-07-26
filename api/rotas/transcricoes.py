"""Rotas de transcrição: criar job, listar/consultar histórico, progresso (WS) e arquivos."""

from __future__ import annotations

import asyncio
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from nucleo import informacoes as informacoes_midia

from .. import bd, trabalhos
from ..configuracao import PASTA_UPLOADS_APP
from ..esquemas import CriarTranscricaoRequest, CriarTranscricaoResposta, InfoMidiaRequest

router = APIRouter()


def _nome_seguro(nome: str) -> str:
    """Remove componentes de caminho e caracteres perigosos do nome enviado."""
    nome = Path(nome).name  # descarta qualquer diretório
    nome = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome)
    return nome or "arquivo"


@router.post("/upload")
async def upload(arquivo: UploadFile):
    """Recebe um arquivo enviado pela interface e o salva em disco, devolvendo o
    caminho local — que depois é usado no POST /api/transcricoes como 'entrada'."""
    PASTA_UPLOADS_APP.mkdir(parents=True, exist_ok=True)
    nome = _nome_seguro(arquivo.filename or "arquivo")
    destino = PASTA_UPLOADS_APP / nome
    # Evita sobrescrever: acrescenta sufixo se já existir.
    if destino.exists():
        base, ext = destino.stem, destino.suffix
        i = 2
        while (PASTA_UPLOADS_APP / f"{base} ({i}){ext}").exists():
            i += 1
        destino = PASTA_UPLOADS_APP / f"{base} ({i}){ext}"

    with open(destino, "wb") as saida:
        while True:
            pedaco = await arquivo.read(1024 * 1024)  # 1 MB por vez
            if not pedaco:
                break
            saida.write(pedaco)
    await arquivo.close()

    # A duração vai junto para a interface já mostrar "1h 12min" assim que o
    # arquivo termina de carregar, sem uma segunda ida ao servidor.
    info = informacoes_midia(destino)
    return {
        "caminho": str(destino),
        "nome": destino.name,
        "duracao_segundos": info["duracao_segundos"],
        "tamanho_bytes": info["tamanho_bytes"],
    }


@router.post("/info-midia")
def info_midia(req: InfoMidiaRequest):
    """Duração e tamanho de um arquivo local, para a interface mostrar antes de
    transcrever. Usado quando o usuário cola um caminho em vez de enviar o arquivo.

    Só lê metadados com o ffprobe — nunca devolve o conteúdo do arquivo."""
    caminho = Path(req.caminho.strip())
    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado nesse caminho.")
    return informacoes_midia(caminho)


_MEDIA_TYPES = {
    "txt": "text/plain; charset=utf-8",
    "srt": "application/x-subrip; charset=utf-8",
    "vtt": "text/vtt; charset=utf-8",
    "json": "application/json; charset=utf-8",
}

# Estados terminais: quando o job já acabou, o WebSocket manda o snapshot e fecha.
_TERMINAIS = trabalhos.STATUS_TERMINAIS


@router.post("", response_model=CriarTranscricaoResposta)
def criar_transcricao(req: CriarTranscricaoRequest):
    id_ = trabalhos.criar_job(req.model_dump())
    return CriarTranscricaoResposta(id=id_, status=trabalhos.NA_FILA)


@router.get("")
def listar(
    limite: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = None,
):
    return bd.listar_transcricoes(limite=limite, offset=offset, status=status)


@router.get("/{id_}")
def detalhe(id_: str):
    registro = bd.obter_transcricao(id_)
    if registro is None:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada.")
    # Enriquecer com o estado em memória, se o job ainda estiver ativo.
    estado = trabalhos.obter_estado(id_)
    if estado:
        registro["estado_ao_vivo"] = estado
    return registro


@router.post("/{id_}/cancelar")
def cancelar(id_: str):
    """Interrompe uma transcrição em andamento.

    O corte não é instantâneo: o worker confere o pedido entre um trecho de
    áudio e o seguinte, então pode levar alguns segundos até parar de fato.
    """
    registro = bd.obter_transcricao(id_)
    if registro is None:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada.")

    status = trabalhos.cancelar_job(id_)
    if status is None:
        # Job não está mais em memória (servidor reiniciado, por exemplo).
        raise HTTPException(
            status_code=409,
            detail="Essa transcrição não está mais em andamento.",
        )
    if status in trabalhos.STATUS_TERMINAIS:
        raise HTTPException(
            status_code=409,
            detail="Essa transcrição já havia terminado.",
        )
    return {"cancelando": True, "status_no_pedido": status}


@router.delete("/{id_}")
def remover(id_: str, apagar_arquivos: bool = False):
    registro = bd.obter_transcricao(id_)
    if registro is None:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada.")
    if apagar_arquivos:
        for caminho in registro.get("arquivos_gerados", []):
            try:
                Path(caminho).unlink(missing_ok=True)
            except OSError:
                pass
    bd.remover_transcricao(id_)
    return {"removido": True}


@router.get("/{id_}/arquivos/{formato}")
def baixar_arquivo(id_: str, formato: str):
    registro = bd.obter_transcricao(id_)
    if registro is None:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada.")

    pasta_saida = Path(registro["pasta_saida"]).resolve()
    for caminho_str in registro.get("arquivos_gerados", []):
        caminho = Path(caminho_str).resolve()
        if caminho.suffix.lstrip(".") == formato:
            # Proteção contra path traversal: o arquivo tem que estar dentro da pasta de saída.
            if pasta_saida not in caminho.parents:
                raise HTTPException(status_code=403, detail="Caminho de arquivo inválido.")
            if not caminho.is_file():
                raise HTTPException(status_code=404, detail="Arquivo não existe mais em disco.")
            return FileResponse(
                caminho,
                media_type=_MEDIA_TYPES.get(formato, "application/octet-stream"),
                filename=caminho.name,
            )
    raise HTTPException(status_code=404, detail=f"Formato '{formato}' não foi gerado para esta transcrição.")


@router.websocket("/{id_}/ws")
async def progresso_ws(websocket: WebSocket, id_: str):
    await websocket.accept()
    ultima_versao = -1
    try:
        while True:
            estado = trabalhos.obter_estado(id_)
            if estado is None:
                # Job não está mais em memória — buscar snapshot final no banco.
                registro = bd.obter_transcricao(id_)
                if registro is None:
                    await websocket.send_json({"tipo": "erro", "mensagem": "Transcrição não encontrada."})
                else:
                    await websocket.send_json({"tipo": "concluido", "transcricao": registro})
                break

            if estado["versao"] != ultima_versao:
                ultima_versao = estado["versao"]
                await websocket.send_json({"tipo": "estado", **estado})

                if estado["status"] in _TERMINAIS:
                    registro = bd.obter_transcricao(id_)
                    if estado["status"] == trabalhos.CONCLUIDO:
                        await websocket.send_json({"tipo": "concluido", "transcricao": registro})
                    elif estado["status"] == trabalhos.CANCELADO:
                        # Tipo próprio: cancelar é escolha do usuário, não falha.
                        await websocket.send_json({"tipo": "cancelado", "transcricao": registro})
                    else:
                        await websocket.send_json(
                            {"tipo": "erro", "mensagem": estado.get("erro") or "Erro na transcrição.",
                             "transcricao": registro}
                        )
                    break

            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
