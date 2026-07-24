import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ModeloInfo } from "../tipos";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

export default function Modelos() {
  const [modelos, setModelos] = useState<ModeloInfo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    carregar();
    return () => { if (pollRef.current) window.clearInterval(pollRef.current); };
  }, []);

  async function carregar() {
    try {
      setModelos(await api.modelos());
    } catch {
      setErro("Não consegui carregar a lista de modelos.");
    } finally {
      setCarregando(false);
    }
  }

  function iniciarPolling() {
    if (pollRef.current) return;
    pollRef.current = window.setInterval(async () => {
      const ms = await api.modelos();
      setModelos(ms);
      if (!ms.some((m) => m.download_status === "baixando")) {
        if (pollRef.current) { window.clearInterval(pollRef.current); pollRef.current = null; }
      }
    }, 2000);
  }

  async function baixar(nome: string) {
    setErro("");
    try {
      await api.baixarModelo(nome);
      setModelos((ms) => ms.map((m) => (m.nome === nome ? { ...m, download_status: "baixando" } : m)));
      iniciarPolling();
    } catch {
      setErro("Não consegui iniciar o download.");
    }
  }

  async function remover(nome: string) {
    if (!confirm(`Remover o modelo "${nome}" do computador? Você pode baixá-lo de novo depois.`)) return;
    try {
      await api.removerModelo(nome);
      carregar();
    } catch {
      setErro("Não consegui remover esse modelo.");
    }
  }

  async function tornarPadrao(nome: string) {
    try {
      await api.definirModeloPadrao(nome);
      carregar();
    } catch {
      /* ignore */
    }
  }

  return (
    <>
      <h3 style={{ marginBottom: "var(--space-2)" }}>Modelos de transcrição</h3>
      <p className="pagina-desc">
        Os modelos são o "cérebro" que reconhece a fala. Modelos maiores são mais precisos, porém
        mais lentos e ocupam mais espaço. Todos rodam localmente e você só baixa uma vez.
      </p>

      <div className="card-kicker" style={{ marginBottom: "var(--space-3)" }}>Motor: Whisper (faster-whisper)</div>

      {erro && <div className="alerta alerta-erro"><span className="icone">⚠️</span><div>{erro}</div></div>}
      {carregando && <div className="vazio">Carregando…</div>}

      <div className="grade-3">
        {modelos.map((m) => (
          <div key={m.nome} className="card blueprint elev-sm" style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            <Canto />
            <div className="card-kicker">
              {m.baixado ? `Baixado · ${formatarMB(m.tamanho_disco_mb)}` : `~${m.tamanho_aprox_mb} MB`}
            </div>
            <div className="card-title">
              {m.rotulo}
              {m.recomendado && <span className="tag tag-accent" style={{ marginLeft: 8 }}>Recomendado</span>}
              {m.e_padrao && <span className="tag tag-neutral" style={{ marginLeft: 6 }}>Padrão</span>}
            </div>
            <p className="card-body" style={{ flex: 1 }}>{m.resumo}</p>

            {m.download_status === "baixando" ? (
              <span className="tag tag-neutral" style={{ alignSelf: "flex-start" }}>
                <span className="girando" style={{ marginRight: 6 }}>⏳</span> Baixando…
              </span>
            ) : m.baixado ? (
              <div className="acoes">
                {!m.e_padrao && <button className="btn btn-ghost" onClick={() => tornarPadrao(m.nome)}>Tornar padrão</button>}
                <button className="btn btn-ghost btn-perigo" onClick={() => remover(m.nome)}>Remover</button>
              </div>
            ) : (
              <button className="btn btn-secondary btn-block blueprint" onClick={() => baixar(m.nome)}>
                <Canto />Baixar
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="card blueprint elev-sm" style={{ marginTop: "var(--space-6)", opacity: 0.85 }}>
        <Canto />
        <div className="card-kicker">Em breve</div>
        <div className="card-title">Outros motores de transcrição</div>
        <p className="card-body">
          Suporte a modelos de outros fornecedores (como NVIDIA NeMo/Parakeet e outros do Hugging
          Face) está planejado. Eles usam um motor diferente do Whisper e serão adicionados aqui
          como opções extras, sem trocar o que já funciona.
        </p>
      </div>
    </>
  );
}

function formatarMB(mb: number | null): string {
  if (mb == null) return "-";
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
}
