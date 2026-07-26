import { useEffect, useState } from "react";
import { api } from "../api";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

const ESTILOS_PADRAO = [
  { chave: "curto", rotulo: "Curto (1-2 parágrafos)", instrucao: "" },
  { chave: "topicos", rotulo: "Tópicos (bullets)", instrucao: "" },
  { chave: "frases_chave", rotulo: "Frases-chave (citações)", instrucao: "" },
  { chave: "executivo", rotulo: "Resumo executivo", instrucao: "" },
  { chave: "personalizado", rotulo: "Personalizado", instrucao: "" },
];

function markdownParaHtml(texto: string): string {
  let html = texto
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^\- (.+)$/gm, "<li>$1</li>")
    .replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>");
  html = "<p>" + html + "</p>";
  html = html.replace(/<li>.+?<\/li>/gs, (m) => `<ul>${m}</ul>`);
  html = html.replace(/<\/ul>\s*<ul>/g, "");
  return html;
}

export default function Resumir() {
  const [ativado, setAtivado] = useState(false);
  const [provedorRotulo, setProvedorRotulo] = useState("");
  const [modelo, setModelo] = useState("");
  const [estilo, setEstilo] = useState("curto");
  const [promptLivre, setPromptLivre] = useState("");
  const [estilosComInstrucao, setEstilosComInstrucao] = useState(ESTILOS_PADRAO);

  const [texto, setTexto] = useState("");
  const [resumo, setResumo] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const [resumindo, setResumindo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => { carregar(); }, []);

  async function carregar() {
    try {
      const configsResp = await api.config();
      setAtivado(configsResp.resumo_ativo === "1");
      setModelo(configsResp.resumo_modelo ?? "");
      setEstilo(configsResp.resumo_estilo ?? "curto");
      const chaveProvedor = configsResp.resumo_provedor ?? "ollama";
      try {
        const provResp = await api.provedoresResumo();
        const prov = provResp.provedores.find((p: any) => p.chave === chaveProvedor);
        setProvedorRotulo(prov?.rotulo ?? chaveProvedor);
        if (provResp.estilos?.length > 0) {
          const estilos = ESTILOS_PADRAO.map((e) => {
            const real = (provResp.estilos as any[]).find((s: any) => s.chave === e.chave);
            return real ? { ...e, instrucao: real.instrucao } : e;
          });
          estilos.push({ chave: "personalizado", rotulo: "Personalizado", instrucao: "" });
          setEstilosComInstrucao(estilos);
          // pre-fill prompt for current style
          const atual = estilos.find((e: any) => e.chave === (configsResp.resumo_estilo ?? "curto"));
          if (atual && atual.instrucao) setPromptLivre(atual.instrucao);
        }
      } catch { /* usa padrao */ }
    } catch {
      setErro("Não consegui carregar as configurações.");
    }
  }

  // Quando muda o estilo, preenche o prompt
  function mudarEstilo(novo: string) {
    setEstilo(novo);
    if (novo === "personalizado") {
      setPromptLivre("");
    } else {
      const e = estilosComInstrucao.find((s: any) => s.chave === novo);
      if (e?.instrucao) setPromptLivre(e.instrucao);
    }
  }

  async function resumir() {
    setErro(null); setResumo(null); setEditando(false);
    if (!ativado) { setErro("Resumo desativado. Ative em Configurações → Resumo por IA."); return; }
    if (!texto.trim()) { setErro("Cole o texto antes de resumir."); return; }

    let cfg: any = {};
    try { cfg = await api.config(); } catch { setErro("Não consegui carregar as configurações."); return; }
    if (cfg.resumo_ativo !== "1") { setErro("Resumo desativado."); return; }

    setResumindo(true);
    try {
      const r = await api.resumir({
        texto,
        config: {
          chave_provedor: cfg.resumo_provedor ?? "ollama",
          chave_api: cfg.resumo_chave_api ?? "",
          modelo: cfg.resumo_modelo ?? "",
          estilo: promptLivre || estilo,
          max_tokens: Number(cfg.resumo_max_tokens ?? "1024"),
        },
      });
      setResumo(r.resumo || "(sem resposta)");
    } catch (e: any) {
      setErro(e?.message ?? "Falha ao resumir.");
    } finally { setResumindo(false); }
  }

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-2)" }}>
        <h3 style={{ margin: 0 }}>Resumir com IA</h3>
        <span className={`tag ${ativado ? "tag-accent" : "tag-outline"}`}>{ativado ? "IA ativa" : "IA desligada"}</span>
      </div>
      <p className="pagina-desc">
        {ativado && provedorRotulo ? (
          <>Provedor: <strong>{provedorRotulo}</strong>{modelo ? ` (${modelo})` : ""}.</>
        ) : ("Ative em Configurações → Resumo por IA.")}
      </p>

      {erro && <div className="alerta alerta-erro" style={{ marginBottom: "var(--space-3)" }}><span className="icone">⚠️</span><div>{erro}</div></div>}

      <div className="card blueprint elev-sm">
        <Canto />
        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label>Texto a resumir</label>
          <textarea className="input" style={{ minHeight: 160, fontFamily: "var(--font-body)" }} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Cole aqui a transcrição. Botão direito → Colar." />
        </div>

        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label>Estilo do resumo</label>
          <select className="input" value={estilo} onChange={(e) => mudarEstilo(e.target.value)}>
            {estilosComInstrucao.map((e: any) => <option key={e.chave} value={e.chave}>{e.rotulo}</option>)}
          </select>
        </div>

        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label>Prompt que será enviado à IA {estilo !== "personalizado" && <span className="check-nota">(editável)</span>}</label>
          <textarea
            className="input"
            style={{ minHeight: 80, fontFamily: "var(--font-body)", fontSize: ".85em" }}
            value={promptLivre}
            onChange={(e) => { setPromptLivre(e.target.value); if (estilo !== "personalizado") setEstilo("personalizado"); }}
            placeholder="Instruções para a IA resumir..."
          />
        </div>

        <div className="acoes">
          <button className="btn btn-primary blueprint" onClick={resumir} disabled={resumindo}>
            <Canto />{resumindo ? "Resumindo..." : "Resumir"}
          </button>
        </div>

        {resumo !== null && (
          <div style={{ marginTop: "var(--space-4)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
              <label style={{ margin: 0 }}>Resumo</label>
              <button
                className="btn btn-ghost"
                onClick={() => setEditando(!editando)}
                style={{ fontSize: ".85em" }}
              >
                {editando ? "👁 Visualizar" : "✏️ Editar"}
              </button>
            </div>

            {editando ? (
              <textarea
                className="input"
                style={{ minHeight: 220, fontFamily: "var(--font-body)", whiteSpace: "pre-wrap" }}
                value={resumo}
                onChange={(e) => setResumo(e.target.value)}
              />
            ) : (
              <div
                className="transcript-box"
                style={{ minHeight: 120, lineHeight: 1.6 }}
                dangerouslySetInnerHTML={{ __html: markdownParaHtml(resumo) }}
              />
            )}

            <div className="acoes" style={{ marginTop: "var(--space-3)" }}>
              <button className="btn btn-secondary blueprint" onClick={() => navigator.clipboard.writeText(resumo)}>
                <Canto />Copiar resumo
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
