import { useEffect, useState } from "react";
import { api } from "../api";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

interface ProvedorInfo {
  chave: string;
  rotulo: string;
  provedor: string;
  url_base_padrao: string;
  modelo_padrao: string;
  precisa_chave: boolean;
}

interface EstiloInfo {
  chave: string;
  rotulo: string;
}

const ESTILOS_RESUMO_PADRAO: EstiloInfo[] = [
  { chave: "curto", rotulo: "Curto (1-2 parágrafos)" },
  { chave: "topicos", rotulo: "Tópicos (bullets)" },
  { chave: "frases_chave", rotulo: "Frases-chave (citações curtas)" },
  { chave: "executivo", rotulo: "Resumo executivo" },
];

export default function Resumir() {
  const [provedores, setProvedores] = useState<ProvedorInfo[]>([]);
  const [estilos, setEstilos] = useState<EstiloInfo[]>(ESTILOS_RESUMO_PADRAO);

  // Configuração aplicada (vem do backend; o usuário pode mexer aqui)
  const [provedorEscolhido, setProvedorEscolhido] = useState("ollama");
  const [chaveApi, setChaveApi] = useState("");
  const [modelo, setModelo] = useState("");
  const [estilo, setEstilo] = useState("curto");
  const [maxTokens, setMaxTokens] = useState(1024);
  const [ativado, setAtivado] = useState(false);

  // Estado da ação de resumir
  const [texto, setTexto] = useState("");
  const [resumo, setResumo] = useState<string | null>(null);
  const [resumindo, setResumindo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    carregar();
  }, []);

  async function carregar() {
    try {
      const [provResp, configsResp] = await Promise.all([
        api.provedoresResumo(),
        api.config(),
      ]);
      setProvedores(provResp.provedores);
      setEstilos(provResp.estilos.length > 0 ? provResp.estilos : ESTILOS_RESUMO_PADRAO);

      // Pré-preenche com a config salva, se houver
      const provedorSalvo = configsResp.resumo_provedor ?? "ollama";
      setProvedorEscolhido(provedorSalvo);
      setChaveApi(configsResp.resumo_chave_api ?? "");
      setAtivado(configsResp.resumo_ativo === "1");
      setModelo(configsResp.resumo_modelo ?? "");
      const prov = provResp.provedores.find((p) => p.chave === provedorSalvo);
      setEstilo(configsResp.resumo_estilo ?? "curto");
      setMaxTokens(Number(configsResp.resumo_max_tokens ?? "1024"));
      // Se o usuário nunca escolheu modelo, sugere o do preset
      if (!configsResp.resumo_modelo && prov) {
        setModelo(prov.modelo_padrao);
      }
    } catch (e) {
      setErro("Não consegui carregar provedores de IA. O servidor Python está rodando?");
    }
  }

  async function ativarESalvar() {
    setSalvando(true);
    setErro(null);
    setAviso(null);
    try {
      await api.atualizarConfig({
        resumo_ativo: true,
        resumo_provedor: provedorEscolhido,
        resumo_chave_api: chaveApi,
        resumo_modelo: modelo,
        resumo_estilo: estilo,
        resumo_max_tokens: maxTokens,
      });
      setAtivado(true);
      setAviso("Configuração salva e ativada. O resumo fica disponível enquanto você não desativar.");
    } catch (e: any) {
      setErro(e?.message ?? "Não consegui salvar.");
    } finally {
      setSalvando(false);
    }
  }

  async function resumir() {
    setErro(null);
    setAviso(null);
    setResumo(null);

    if (!ativado) {
      setErro("Ative o resumo por IA primeiro (marque a opção abaixo e salve).");
      return;
    }
    if (!texto.trim()) {
      setErro("Cole ou escreva o texto da transcrição antes de resumir.");
      return;
    }

    setResumindo(true);
    try {
      const r = await api.resumir({
        texto,
        chave_provedor: provedorEscolhido,
        chave_api: chaveApi,
        modelo,
        estilo,
        max_tokens: maxTokens,
      });
      setResumo(r.resumo || "(sem resposta)");
    } catch (e: any) {
      setErro(e?.message ?? "Falha ao resumir. O provedor escolhido está respondendo?");
    } finally {
      setResumindo(false);
    }
  }

  async function desativar() {
    setSalvando(true);
    setErro(null);
    setAviso(null);
    try {
      await api.atualizarConfig({ resumo_ativo: false });
      setAtivado(false);
      setAviso("Resumo por IA desativado. A transcrição continua 100% local.");
    } catch (e: any) {
      setErro(e?.message ?? "Não consegui desativar.");
    } finally {
      setSalvando(false);
    }
  }

  const provedor = provedores.find((p) => p.chave === provedorEscolhido);

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-2)" }}>
        <h3 style={{ margin: 0 }}>Resumir com IA</h3>
        <span
          className={`tag ${ativado ? "tag-accent" : "tag-outline"}`}
          title="Quando desativado, nenhum texto sai do seu computador."
        >
          {ativado ? "IA ativa" : "IA desligada"}
        </span>
      </div>
      <p className="pagina-desc">
        Pede um resumo do texto transcrito a um provedor de IA. Por padrão
        este recurso está <strong>desligado</strong> — ativar aqui faz o
        programa enviar o texto para o provedor escolhido <em>só</em> quando
        você pedir um resumo (não na transcrição).
        Provedores locais (LM Studio, Ollama) ficam na sua máquina; os de
        nuvem (Groq, OpenAI, Claude, Mistral, OpenRouter) exigem chave e
        enviam para os servidores deles.
      </p>

      {erro && (
        <div className="alerta alerta-erro" style={{ marginBottom: "var(--space-3)" }}>
          <span className="icone">⚠️</span>
          <div>{erro}</div>
        </div>
      )}
      {aviso && (
        <div className="alerta alerta-info" style={{ marginBottom: "var(--space-3)" }}>
          <span className="icone">ℹ️</span>
          <div>{aviso}</div>
        </div>
      )}

      <div className="card blueprint elev-sm" style={{ marginBottom: "var(--space-4)" }}>
        <Canto />
        <h3 style={{ marginTop: 0 }}>Configuração</h3>

        {!ativado && (
          <div className="alerta alerta-info" style={{ marginBottom: "var(--space-3)" }}>
            <span className="icone">🔒</span>
            <div>
              <strong>Recurso desligado.</strong> Nada sai do seu computador.
              Para usar, ative abaixo e salve.
            </div>
          </div>
        )}

        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label>
            <input
              type="checkbox"
              checked={ativado}
              onChange={(e) => setAtivado(e.target.checked)}
              style={{ marginRight: 6 }}
            />
            Ativar resumo por IA
          </label>
        </div>

        {ativado && (
          <>
            <div className="field" style={{ marginBottom: "var(--space-3)" }}>
              <label>Provedor</label>
              <select
                className="input"
                value={provedorEscolhido}
                onChange={(e) => {
                  setProvedorEscolhido(e.target.value);
                  const novo = provedores.find((p) => p.chave === e.target.value);
                  if (novo) setModelo(novo.modelo_padrao);
                }}
              >
                {provedores.map((p) => (
                  <option key={p.chave} value={p.chave}>{p.rotulo}</option>
                ))}
              </select>
              {provedor && (
                <div className="check-nota">
                  {provedor.provedor === "anthropic"
                    ? "API da Anthropic."
                    : "Compatível com a API OpenAI."}
                  {provedor.precisa_chave && " Precisa de chave."}
                </div>
              )}
            </div>

            <div className="field" style={{ marginBottom: "var(--space-3)" }}>
              <label>
                Chave de API
                {!provedor?.precisa_chave && " (opcional para provedores locais)"}
              </label>
              <input
                className="input"
                type="password"
                value={chaveApi}
                onChange={(e) => setChaveApi(e.target.value)}
                placeholder={
                  provedor?.precisa_chave
                    ? "Cole sua chave aqui (fica só no seu computador)"
                    : "Vazia se for local sem autenticação"
                }
              />
            </div>

            <div className="field" style={{ marginBottom: "var(--space-3)" }}>
              <label>Modelo</label>
              <input
                className="input"
                value={modelo}
                onChange={(e) => setModelo(e.target.value)}
                placeholder={
                  provedor?.modelo_padrao
                    ? `Padrão do ${provedor.rotulo}: ${provedor.modelo_padrao}`
                    : "Ex.: llama3.2, gpt-4o-mini"
                }
              />
            </div>

            <div className="field" style={{ marginBottom: "var(--space-3)" }}>
              <label>Estilo do resumo</label>
              <select
                className="input"
                value={estilo}
                onChange={(e) => setEstilo(e.target.value)}
              >
                {estilos.map((e) => (
                  <option key={e.chave} value={e.chave}>{e.rotulo}</option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>Tamanho máximo: {maxTokens} tokens</label>
              <input
                type="range"
                min={128}
                max={4096}
                step={64}
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
              />
            </div>
          </>
        )}

        <div className="acoes" style={{ marginTop: "var(--space-4)" }}>
          {ativado ? (
            <>
              <button className="btn btn-ghost" onClick={desativar} disabled={salvando}>
                {salvando ? "..." : "Desativar e manter config"}
              </button>
              <button className="btn btn-secondary blueprint" onClick={ativarESalvar} disabled={salvando}>
                <Canto />
                {salvando ? "Salvando..." : "Salvar alterações"}
              </button>
            </>
          ) : (
            <button className="btn btn-primary blueprint" onClick={ativarESalvar} disabled={salvando}>
              <Canto />
              {salvando ? "Salvando..." : "Ativar e salvar"}
            </button>
          )}
        </div>
      </div>

      <div className="card blueprint elev-sm">
        <Canto />
        <h3 style={{ marginTop: 0 }}>Resumir agora</h3>

        <div className="field" style={{ marginBottom: "var(--space-3)" }}>
          <label>
            Texto a resumir{" "}
            <span className="check-nota" style={{ display: "inline" }}>
              (cole do Histórico, ou digite)
            </span>
          </label>
          <textarea
            className="input"
            style={{ minHeight: 180, fontFamily: "var(--font-body)" }}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Cole aqui a transcrição. O texto só sai do seu computador quando você clicar em Resumir (e só com o provedor que você escolheu)."
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
            <div
              className="transcript-box"
              style={{ minHeight: 100, whiteSpace: "pre-wrap" }}
            >
              {resumo}
            </div>
            <div className="acoes" style={{ marginTop: "var(--space-3)" }}>
              <button
                className="btn btn-secondary blueprint"
                onClick={() => navigator.clipboard.writeText(resumo)}
              >
                <Canto />Copiar resumo
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
