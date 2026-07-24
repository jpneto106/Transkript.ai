import { useEffect, useState } from "react";
import { api } from "../api";
import type { Dicionario } from "../tipos";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

export default function Dicionarios() {
  const [itens, setItens] = useState<Dicionario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [editando, setEditando] = useState<Dicionario | "novo" | null>(null);

  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [termosTexto, setTermosTexto] = useState("");
  const [erro, setErro] = useState("");

  useEffect(() => { carregar(); }, []);

  async function carregar() {
    setCarregando(true);
    try {
      setItens(await api.dicionarios());
    } catch {
      /* ignore */
    } finally {
      setCarregando(false);
    }
  }

  function abrirNovo() {
    setEditando("novo");
    setNome("");
    setDescricao("");
    setTermosTexto("");
    setErro("");
  }

  function abrirEdicao(d: Dicionario) {
    setEditando(d);
    setNome(d.nome);
    setDescricao(d.descricao || "");
    setTermosTexto(d.termos.join("\n"));
    setErro("");
  }

  function termosDoTexto(): string[] {
    // Aceita termos separados por vírgula ou por linha.
    return termosTexto
      .split(/[\n,]+/)
      .map((t) => t.trim())
      .filter(Boolean);
  }

  async function salvar() {
    if (!nome.trim()) return setErro("Dê um nome ao dicionário.");
    const dados = { nome: nome.trim(), descricao: descricao.trim() || null, termos: termosDoTexto() };
    try {
      if (editando === "novo") await api.criarDicionario(dados);
      else if (editando) await api.atualizarDicionario(editando.id, dados);
      setEditando(null);
      carregar();
    } catch {
      setErro("Não consegui salvar o dicionário.");
    }
  }

  async function remover(d: Dicionario) {
    if (!confirm(`Remover o dicionário "${d.nome}"?`)) return;
    try {
      await api.removerDicionario(d.id);
      carregar();
    } catch {
      /* ignore */
    }
  }

  // ---- formulário de criação/edição ----
  if (editando) {
    return (
      <>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-6)" }}>
          <h3 style={{ margin: 0 }}>{editando === "novo" ? "Novo dicionário" : "Editar dicionário"}</h3>
          <button className="btn btn-ghost" onClick={() => setEditando(null)}>Cancelar</button>
        </div>

        {erro && <div className="alerta alerta-erro"><span className="icone">⚠️</span><div>{erro}</div></div>}

        <div className="card blueprint elev-sm">
          <Canto />
          <div className="field" style={{ marginBottom: "var(--space-4)" }}>
            <label>Nome do dicionário</label>
            <input className="input" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Termos de medicina" />
          </div>
          <div className="field" style={{ marginBottom: "var(--space-4)" }}>
            <label>Descrição (opcional)</label>
            <input className="input" value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Para que serve este dicionário" />
          </div>
          <div className="field">
            <label>Termos (um por linha, ou separados por vírgula)</label>
            <textarea
              className="input"
              style={{ minHeight: 200, fontFamily: "var(--font-body)" }}
              value={termosTexto}
              onChange={(e) => setTermosTexto(e.target.value)}
              placeholder={"Ex.:\nangioplastia\nSaitama\nOne Punch Man\nnomes próprios, siglas, jargões..."}
            />
            <div className="check-nota">
              Esses termos são passados ao modelo como pista (initial_prompt), ajudando a reconhecer
              nomes próprios e palavras específicas do assunto. {termosDoTexto().length} termo(s).
            </div>
          </div>
          <div className="acoes" style={{ marginTop: "var(--space-5)" }}>
            <button className="btn btn-primary blueprint" onClick={salvar}><Canto />Salvar</button>
            <button className="btn btn-ghost" onClick={() => setEditando(null)}>Cancelar</button>
          </div>
        </div>
      </>
    );
  }

  // ---- lista ----
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-2)", gap: "var(--space-4)" }}>
        <h3 style={{ margin: 0 }}>Dicionários de termos</h3>
        <button className="btn btn-primary blueprint" onClick={abrirNovo}><Canto />+ Novo dicionário</button>
      </div>
      <p className="pagina-desc">
        Cadastre listas de palavras específicas (nomes próprios, termos técnicos, siglas) para o
        modelo reconhecer melhor. Depois é só escolher o dicionário na tela de Nova transcrição.
      </p>

      {carregando && <div className="vazio">Carregando…</div>}

      {!carregando && itens.length === 0 && (
        <div className="vazio">
          <div className="vazio-icone">📖</div>
          Nenhum dicionário ainda. Crie um para melhorar a transcrição de termos específicos.
        </div>
      )}

      {itens.map((d) => (
        <div key={d.id} className="card blueprint elev-sm" style={{ marginBottom: "var(--space-3)", flexDirection: "row", alignItems: "center", gap: "var(--space-4)", display: "flex" }}>
          <Canto />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="card-title">{d.nome}</div>
            <div className="card-body" style={{ margin: "2px 0 0" }}>
              {d.descricao ? d.descricao + " · " : ""}{d.termos.length} termo(s)
            </div>
          </div>
          <div className="acoes">
            <button className="btn btn-ghost" onClick={() => abrirEdicao(d)}>Editar</button>
            <button className="btn btn-ghost btn-perigo" onClick={() => remover(d)}>Remover</button>
          </div>
        </div>
      ))}
    </>
  );
}
