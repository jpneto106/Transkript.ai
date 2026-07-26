import { useEffect, useState } from "react";
import { api } from "../api";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

export default function Resumir() {
  const [ativado, setAtivado] = useState(false);
  const [provedorRotulo, setProvedorRotulo] = useState("");
  const [modelo, setModelo] = useState("");

  const [texto, setTexto] = useState("");
  const [resumo, setResumo] = useState<string | null>(null);
  const [resumindo, setResumindo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    carregar();
  }, []);

  async function carregar() {
    try {
      const configsResp = await api.config();
      const ativo = configsResp.resumo_ativo === "1";
      setAtivado(ativo);
      const chaveProvedor = configsResp.resumo_provedor ?? "ollama";
      setModelo(configsResp.resumo_modelo ?? "");

      // Tenta descobrir o rótulo do provedor
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

    if (!ativado) {
      setErro("O resumo por IA está desativado. Ative em Configurações > Resumo por IA.");
      return;
    }
    if (!texto.trim()) {
      setErro("Cole o texto da transcrição antes de resumir.");
      return;
    }

    // Recarrega as configs para pegar dados atualizados
    let cfg: any = {};
    try {
      cfg = await api.config();
    } catch {
      setErro("Não consegui carregar as configurações de IA.");
      return;
    }

    if (cfg.resumo_ativo !== "1") {
      setErro("O resumo por IA está desativado.");
      return;
    }

    setResumindo(true);
    try {
      const r = await api.resumir({
        texto,
        config: {
          chave_provedor: cfg.resumo_provedor ?? "ollama",
          chave_api: cfg.resumo_chave_api ?? "",
          modelo: cfg.resumo_modelo ?? "",
          estilo: cfg.resumo_estilo ?? "curto",
          max_tokens: Number(cfg.resumo_max_tokens ?? "1024"),
        },
      });
      setResumo(r.resumo || "(sem resposta)");
    } catch (e: any) {
      setErro(e?.message ?? "Falha ao resumir. O provedor está rodando?");
    } finally {
      setResumindo(false);
    }
  }

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-2)" }}>
        <h3 style={{ margin: 0 }}>Resumir com IA</h3>
        <span className={`tag ${ativado ? "tag-accent" : "tag-outline"}`}>
          {ativado ? "IA ativa" : "IA desligada"}
        </span>
      </div>
      <p className="pagina-desc">
        Resume o texto colado usando o provedor configurado em{" "}
        <strong>Configurações → Resumo por IA</strong>.
        {ativado && provedorRotulo && (
          <> Provedor atual: <strong>{provedorRotulo}</strong>{modelo ? ` (${modelo})` : ""}.</>
        )}
        {!ativado && " Ative o recurso em Configurações para usar."}
      </p>

      {erro && (
        <div className="alerta alerta-erro" style={{ marginBottom: "var(--space-3)" }}>
          <span className="icone">⚠️</span>
          <div>{erro}</div>
        </div>
      )}

      <div className="card blueprint elev-sm">
        <Canto />
        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label>Texto a resumir</label>
          <textarea
            className="input"
            style={{ minHeight: 220, fontFamily: "var(--font-body)" }}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Cole aqui a transcrição. Use o botão direito → Colar."
          />
        </div>

        <div className="acoes">
          <button className="btn btn-primary blueprint" onClick={resumir} disabled={resumindo}>
            <Canto />
            {resumindo ? "Resumindo..." : "Resumir"}
          </button>
        </div>

        {resumo !== null && (
          <div style={{ marginTop: "var(--space-4)" }}>
            <h4 style={{ margin: "0 0 var(--space-2)" }}>Resumo</h4>
            <div className="transcript-box" style={{ minHeight: 100, whiteSpace: "pre-wrap" }}>
              {resumo}
            </div>
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
