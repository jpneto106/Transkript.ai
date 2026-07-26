// Cliente da API. Em produção (pywebview) o frontend é servido pela própria API,
// então usamos caminhos relativos. Em dev (Vite na 5173), apontamos para a 8000.

import type {
  Dicionario,
  InfoMidia,
  ModeloInfo,
  Opcoes,
  ParametrosTranscricao,
  RespostaUpload,
  Transcricao,
} from "./tipos";

const EM_DEV = import.meta.env.DEV;
const BASE = EM_DEV ? "http://127.0.0.1:8000" : "";

function baseWS(): string {
  if (EM_DEV) return "ws://127.0.0.1:8000";
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}`;
}

async function json<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detalhe = `Erro ${resp.status}`;
    try {
      const corpo = await resp.json();
      if (corpo?.detail) detalhe = corpo.detail;
    } catch {
      /* sem corpo JSON */
    }
    throw new Error(detalhe);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  async saude(): Promise<boolean> {
    try {
      const r = await fetch(`${BASE}/api/saude`);
      return r.ok;
    } catch {
      return false;
    }
  },

  async opcoes(): Promise<Opcoes> {
    return json(await fetch(`${BASE}/api/opcoes`));
  },

  async config(): Promise<Record<string, string>> {
    return json(await fetch(`${BASE}/api/config`));
  },

  async atualizarConfig(payload: Record<string, unknown>): Promise<Record<string, string>> {
    return json(
      await fetch(`${BASE}/api/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    );
  },

  async provedoresResumo(): Promise<{
    provedores: { chave: string; rotulo: string; provedor: string; url_base_padrao: string; modelo_padrao: string; precisa_chave: boolean }[];
    estilos: { chave: string; rotulo: string }[];
  }> {
    return json(await fetch(`${BASE}/api/provedores`));
  },

  async resumir(payload: {
    texto: string;
    chave_provedor: string;
    chave_api: string;
    modelo: string;
    estilo: string;
    max_tokens: number;
  }): Promise<{ resumo: string }> {
    return json(
      await fetch(`${BASE}/api/resumos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    );
  },

  async definirModeloPadrao(modelo: string): Promise<Record<string, string>> {
    return json(
      await fetch(`${BASE}/api/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ modelo_padrao: modelo }),
      }),
    );
  },

  async modelos(): Promise<ModeloInfo[]> {
    return json(await fetch(`${BASE}/api/modelos`));
  },

  async baixarModelo(nome: string): Promise<void> {
    await json(await fetch(`${BASE}/api/modelos/${nome}/baixar`, { method: "POST" }));
  },

  async progressoModelo(nome: string): Promise<{ nome: string; status: string | null }> {
    return json(await fetch(`${BASE}/api/modelos/${nome}/progresso`));
  },

  async removerModelo(nome: string): Promise<void> {
    await json(await fetch(`${BASE}/api/modelos/${nome}`, { method: "DELETE" }));
  },

  async enviarArquivo(arquivo: File, aoProgredir?: (pct: number) => void): Promise<RespostaUpload> {
    // Usa XMLHttpRequest para ter progresso de upload (fetch não expõe upload progress).
    return new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("arquivo", arquivo);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${BASE}/api/transcricoes/upload`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && aoProgredir) aoProgredir(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
        else reject(new Error("Falha ao enviar o arquivo."));
      };
      xhr.onerror = () => reject(new Error("Falha ao enviar o arquivo."));
      xhr.send(form);
    });
  },

  async criarTranscricao(p: ParametrosTranscricao): Promise<{ id: string; status: string }> {
    return json(
      await fetch(`${BASE}/api/transcricoes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p),
      }),
    );
  },

  /** Duração e tamanho de um arquivo local (usado quando o usuário cola um caminho). */
  async infoMidia(caminho: string): Promise<InfoMidia> {
    return json(
      await fetch(`${BASE}/api/transcricoes/info-midia`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ caminho }),
      }),
    );
  },

  /** Pede o cancelamento. A parada não é imediata — leva alguns segundos. */
  async cancelarTranscricao(id: string): Promise<void> {
    await json(await fetch(`${BASE}/api/transcricoes/${id}/cancelar`, { method: "POST" }));
  },

  async historico(): Promise<Transcricao[]> {
    return json(await fetch(`${BASE}/api/transcricoes`));
  },

  async removerTranscricao(id: string, apagarArquivos: boolean): Promise<void> {
    await json(
      await fetch(`${BASE}/api/transcricoes/${id}?apagar_arquivos=${apagarArquivos}`, {
        method: "DELETE",
      }),
    );
  },

  urlArquivo(id: string, formato: string): string {
    return `${BASE}/api/transcricoes/${id}/arquivos/${formato}`;
  },

  async textoArquivo(id: string, formato: string): Promise<string> {
    const r = await fetch(this.urlArquivo(id, formato));
    if (!r.ok) throw new Error("Não consegui carregar o texto.");
    return r.text();
  },

  wsProgresso(id: string): WebSocket {
    return new WebSocket(`${baseWS()}/api/transcricoes/${id}/ws`);
  },

  // ---------------------------------------------------------- dicionários
  async dicionarios(): Promise<Dicionario[]> {
    return json(await fetch(`${BASE}/api/dicionarios`));
  },

  async criarDicionario(d: { nome: string; descricao: string | null; termos: string[] }): Promise<Dicionario> {
    return json(
      await fetch(`${BASE}/api/dicionarios`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(d),
      }),
    );
  },

  async atualizarDicionario(
    id: string,
    d: { nome: string; descricao: string | null; termos: string[] },
  ): Promise<Dicionario> {
    return json(
      await fetch(`${BASE}/api/dicionarios/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(d),
      }),
    );
  },

  async removerDicionario(id: string): Promise<void> {
    await json(await fetch(`${BASE}/api/dicionarios/${id}`, { method: "DELETE" }));
  },
};

// Ponte com o pywebview (diálogo nativo de arquivo). Só existe dentro do app desktop.
export interface PyWebviewApi {
  escolher_arquivo: () => Promise<string[]>;
  abrir_pasta: (caminho: string) => Promise<boolean>;
}

export function pywebview(): PyWebviewApi | null {
  const w = window as unknown as { pywebview?: { api?: PyWebviewApi } };
  return w.pywebview?.api ?? null;
}
