import { useEffect, useMemo, useState } from "react";
import { api, pywebview } from "../api";
import type { Transcricao } from "../tipos";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

export default function Historico() {
  const [itens, setItens] = useState<Transcricao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [busca, setBusca] = useState("");
  const [aberto, setAberto] = useState<Transcricao | null>(null);
  const [texto, setTexto] = useState("");

  useEffect(() => { carregar(); }, []);

  async function carregar() {
    setCarregando(true);
    try {
      setItens(await api.historico());
    } catch {
      /* ignore */
    } finally {
      setCarregando(false);
    }
  }

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return itens;
    return itens.filter((t) => (t.nome_arquivo || t.entrada_original).toLowerCase().includes(q));
  }, [itens, busca]);

  async function abrir(t: Transcricao) {
    setAberto(t);
    setTexto("");
    if (t.formatos.includes("txt")) {
      try {
        setTexto(await api.textoArquivo(t.id, "txt"));
      } catch {
        setTexto("(não foi possível carregar o texto — o arquivo pode ter sido movido)");
      }
    }
  }

  async function remover(t: Transcricao) {
    if (!confirm(`Remover "${t.nome_arquivo}" do histórico e apagar os arquivos gerados?`)) return;
    try {
      await api.removerTranscricao(t.id, true);
      carregar();
    } catch {
      /* ignore */
    }
  }

  const temPy = pywebview() !== null;

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-6)", gap: "var(--space-4)" }}>
        <h3 style={{ margin: 0 }}>Histórico de transcrições</h3>
        <input
          className="input"
          placeholder="Buscar por nome do arquivo..."
          style={{ maxWidth: 280 }}
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
        />
      </div>

      {carregando && <div className="vazio">Carregando…</div>}

      {!carregando && filtrados.length === 0 && (
        <div className="vazio">
          <div className="vazio-icone">🕑</div>
          {itens.length === 0 ? "Você ainda não fez nenhuma transcrição." : "Nenhum resultado para essa busca."}
        </div>
      )}

      {filtrados.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Arquivo</th><th>Duração</th><th>Idioma</th><th>Data</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            {filtrados.map((t) => (
              <tr key={t.id}>
                <td style={{ wordBreak: "break-all" }}>{t.nome_arquivo || t.entrada_original}</td>
                <td className="text-muted">{t.duracao_audio != null ? formatarTempo(t.duracao_audio) : "—"}</td>
                <td className="text-muted">{t.idioma_detectado ? t.idioma_detectado.toUpperCase() : "—"}</td>
                <td className="text-muted">{formatarData(t.criado_em)}</td>
                <td>
                  {t.status === "concluido" && <span className="tag tag-accent">Concluído</span>}
                  {t.status === "erro" && <span className="tag tag-erro">Falhou</span>}
                  {t.status !== "concluido" && t.status !== "erro" && <span className="tag tag-neutral">Em andamento</span>}
                </td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  {t.status === "concluido" && (
                    <button className="btn btn-ghost btn-icon" aria-label="Abrir" onClick={() => abrir(t)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" /><circle cx="12" cy="12" r="3" />
                      </svg>
                    </button>
                  )}
                  <button className="btn btn-ghost btn-icon btn-perigo" aria-label="Remover" onClick={() => remover(t)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {aberto && (
        <div className="dialog-backdrop" style={{ position: "fixed", inset: 0, display: "grid", placeItems: "center", padding: "var(--space-6)", background: "color-mix(in srgb, #000 55%, transparent)", zIndex: 100 }} onClick={() => setAberto(null)}>
          <div className="card blueprint elev-sm" style={{ width: "min(760px, 100%)", maxHeight: "85vh", overflowY: "auto", background: "var(--color-bg)" }} onClick={(e) => e.stopPropagation()}>
            <Canto />
            <div className="cabecalho-resultado" style={{ marginBottom: "var(--space-3)" }}>
              <h4 style={{ margin: 0, wordBreak: "break-all" }}>{aberto.nome_arquivo}</h4>
              <button className="btn btn-ghost" onClick={() => setAberto(null)}>Fechar</button>
            </div>
            {aberto.mensagem_erro && (
              <div className="alerta alerta-erro"><span className="icone">⚠️</span><div>{aberto.mensagem_erro}</div></div>
            )}
            {texto && <div className="transcript-box" style={{ minHeight: 200 }}>{texto}</div>}
            <div className="acoes" style={{ marginTop: "var(--space-4)" }}>
              {texto && <button className="btn btn-secondary blueprint" onClick={() => navigator.clipboard.writeText(texto)}><Canto />Copiar</button>}
              {aberto.formatos.map((f) => (
                <a key={f} className="btn btn-secondary blueprint" href={api.urlArquivo(aberto.id, f)} download><Canto />⬇ {f.toUpperCase()}</a>
              ))}
              {temPy && <button className="btn btn-secondary blueprint" onClick={() => pywebview()?.abrir_pasta(aberto.pasta_saida)}><Canto />📂 Pasta</button>}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function formatarData(iso: string): string {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}
function formatarTempo(segundos: number): string {
  const s = Math.max(0, Math.round(segundos));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}
