import { useEffect, useState } from "react";
import { api } from "../api";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

const ESTILOS_PADRAO = [
  { chave: "curto", rotulo: "Curto (1-2 parágrafos)" },
  { chave: "topicos", rotulo: "Tópicos (bullets)" },
  { chave: "frases_chave", rotulo: "Frases-chave (citações)" },
  { chave: "executivo", rotulo: "Resumo executivo" },
  { chave: "personalizado", rotulo: "Personalizado (prompt livre)" },
];

export default function Resumir() {
  const [ativado, setAtivado] = useState(false);
  const [provedorRotulo, setProvedorRotulo] = useState("");
  const [modelo, setModelo] = useState("");
  const [estilo, setEstilo] = useState("curto");
  const [promptPersonalizado, setPromptPersonalizado] = useState("");

  const [texto, setTexto] = useState("");
  const [resumo, setResumo] = useState<string | null>(null);
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
      } catch {
        setProvedorRotulo(chaveProvedor);
      }
    } catch {
      setErro("Não consegui carregar as configurações.");
    }
  }

  async function resumir() {
    setErro(null);
    setResumo(null);
    if (!ativado) { setErro("O resumo por IA está desativado. Ative em Configurações → Resumo por IA."); return; }
    if (!texto.trim()) { setErro("Cole o texto da transcrição antes de resumir."); return; }

    let cfg: any = {};
    try { cfg = await api.config(); } catch { setErro("Não consegui carregar as configurações."); return; }
    if (cfg.resumo_ativo !== "1") { setErro("Resumo por IA desativado."); return; }

    setResumindo(true);
    try {
      const r = await api.resumir({
        texto,
        config: {
          chave_provedor: cfg.resumo_provedor ?? "ollama",
          chave_api: cfg.resumo_chave_api ?? "",
          modelo: cfg.resumo_modelo ?? "",
          estilo: estilo === "personalizado" ? promptPersonalizado : estilo,
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
          <>Provedor: <strong>{provedorRotulo}</strong>{modelo ? ` (${modelo})` : ""}. Configure em <strong>Configurações → Resumo por IA</strong>.</>
        ) : (
          <>Ative o recurso em <strong>Configurações → Resumo por IA</strong>.</>
        )}
      </p>

      {erro && <div className="alerta alerta-erro" style={{ marginBottom: "var(--space-3)" }}><span className="icone">⚠️</span><div>{erro}</div></div>}

      <div className="card blueprint elev-sm">
        <Canto />
        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label>Texto a resumir</label>
          <textarea className="input" style={{ minHeight: 180, fontFamily: "var(--font-body)" }} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Cole aqui a transcrição. Botão direito → Colar." />
        </div>

        <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "end", marginBottom: "var(--space-3)" }}>
          <div className="field" style={{ flex: 1 }}>
            <label>Estilo do resumo</label>
            <select className="input" value={estilo} onChange={(e) => setEstilo(e.target.value)}>
              {ESTILOS_PADRAO.map((e) => <option key={e.chave} value={e.chave}>{e.rotulo}</option>)}
            </select>
          </div>
          <button className="btn btn-primary blueprint" onClick={resumir} disabled={resumindo}>
            <Canto />{resumindo ? "Resumindo..." : "Resumir"}
          </button>
        </div>

        {estilo === "personalizado" && (
          <div className="field" style={{ marginBottom: "var(--space-3)" }}>
            <label>System prompt (instruções para a IA)</label>
            <textarea
              className="input"
              style={{ minHeight: 100, fontFamily: "var(--font-body)" }}
              value={promptPersonalizado}
              onChange={(e) => setPromptPersonalizado(e.target.value)}
              placeholder="Ex.: Resuma em tópicos com emojis. Destaque nomes próprios em negrito. Use ## para seções."
            />
          </div>
        )}

        {resumo !== null && (
          <div style={{ marginTop: "var(--space-3)" }}>
            <label>Resumo (editável — clique e altere antes de copiar)</label>
            <textarea
              className="input"
              style={{ minHeight: 200, fontFamily: "var(--font-body)", whiteSpace: "pre-wrap" }}
              value={resumo}
              onChange={(e) => setResumo(e.target.value)}
            />
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
