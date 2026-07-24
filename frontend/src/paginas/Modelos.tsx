import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ModeloInfo } from "../tipos";

export default function Modelos() {
  const [modelos, setModelos] = useState<ModeloInfo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    carregar();
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
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
      // Para o polling quando não há mais nada baixando.
      if (!ms.some((m) => m.download_status === "baixando")) {
        if (pollRef.current) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    }, 2000);
  }

  async function baixar(nome: string) {
    setErro("");
    try {
      await api.baixarModelo(nome);
      setModelos((ms) =>
        ms.map((m) => (m.nome === nome ? { ...m, download_status: "baixando" } : m)),
      );
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
      <h1 className="pagina-titulo">Modelos de transcrição</h1>
      <p className="pagina-desc">
        Os modelos são o "cérebro" que reconhece a fala. Modelos maiores entendem melhor, mas ocupam
        mais espaço e demoram mais. Você só precisa baixar uma vez.
      </p>

      {erro && (
        <div className="alerta alerta-erro">
          <span className="icone">⚠️</span>
          <div>{erro}</div>
        </div>
      )}

      {carregando && <div className="vazio">Carregando…</div>}

      {modelos.map((m) => (
        <div key={m.nome} className={`modelo-card ${m.e_padrao ? "padrao" : ""}`}>
          <span style={{ fontSize: 24 }}>{m.baixado ? "📦" : "☁️"}</span>
          <div className="modelo-info">
            <div className="modelo-nome">
              {m.rotulo}
              {m.recomendado && <span className="badge badge-primaria">Recomendado</span>}
              {m.e_padrao && <span className="badge badge-sucesso">Padrão</span>}
            </div>
            <div className="modelo-resumo">
              {m.resumo}
              {" · "}
              {m.baixado
                ? `Baixado (${formatarMB(m.tamanho_disco_mb)})`
                : `Download de ~${m.tamanho_aprox_mb} MB`}
            </div>
          </div>
          <div className="modelo-acoes">
            {m.download_status === "baixando" ? (
              <span className="badge badge-neutro">
                <span className="girando">⏳</span> Baixando…
              </span>
            ) : m.baixado ? (
              <>
                {!m.e_padrao && (
                  <button className="btn-fantasma" onClick={() => tornarPadrao(m.nome)}>
                    Tornar padrão
                  </button>
                )}
                <button className="btn-fantasma btn-perigo" onClick={() => remover(m.nome)}>
                  Remover
                </button>
              </>
            ) : (
              <button className="btn btn-primario" onClick={() => baixar(m.nome)}>
                ⬇️ Baixar
              </button>
            )}
          </div>
        </div>
      ))}
    </>
  );
}

function formatarMB(mb: number | null): string {
  if (mb == null) return "-";
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
}
