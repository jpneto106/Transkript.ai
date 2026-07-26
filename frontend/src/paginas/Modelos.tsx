import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ModeloInfo } from "../tipos";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

/** Motores de transcrição, na ordem em que aparecem na tela. */
const MOTORES = [
  {
    chave: "whisper",
    rotulo: "Whisper",
    descricao: "Da OpenAI. Entende praticamente qualquer idioma e detecta o idioma sozinho.",
    semSuporte: "O motor Whisper não está instalado neste computador.",
  },
  {
    chave: "nvidia",
    rotulo: "NVIDIA",
    descricao:
      "Bem mais rápidos que o Whisper e ocupam menos espaço, mas cada um entende um conjunto " +
      "limitado de idiomas — confira antes de escolher.",
    semSuporte:
      "O motor NVIDIA não está instalado neste computador. Estes modelos aparecem aqui apenas " +
      "para você conhecer as opções.",
  },
];

interface Props {
  /** Muda quando uma transcrição termina; dispara a releitura da lista. */
  sinalRecarregar?: number;
}

export default function Modelos({ sinalRecarregar = 0 }: Props) {
  const [modelos, setModelos] = useState<ModeloInfo[]>([]);
  const [motoresOk, setMotoresOk] = useState<Record<string, boolean>>({});
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const pollRef = useRef<number | null>(null);

  // Só ao desmontar de vez: um download em andamento não pode perder o polling
  // quando o usuário troca de aba.
  useEffect(() => {
    return () => { if (pollRef.current) window.clearInterval(pollRef.current); };
  }, []);

  useEffect(() => { carregar(); }, [sinalRecarregar]);

  async function carregar() {
    try {
      const [ms, ops] = await Promise.all([api.modelos(), api.opcoes()]);
      setModelos(ms);
      setMotoresOk(ops.motores || {});
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

      {erro && <div className="alerta alerta-erro"><span className="icone">⚠️</span><div>{erro}</div></div>}
      {carregando && <div className="vazio">Carregando…</div>}

      {MOTORES.map((motor) => {
        const doMotor = modelos.filter((m) => m.motor === motor.chave);
        if (doMotor.length === 0) return null;
        const instalado = motoresOk[motor.chave] !== false;

        return (
          <div key={motor.chave} style={{ marginBottom: "var(--space-6)" }}>
            <div className="card-kicker" style={{ marginBottom: "var(--space-2)" }}>
              Motor: {motor.rotulo}
              {!instalado && <span className="tag tag-neutral" style={{ marginLeft: 8 }}>não instalado</span>}
            </div>
            <p className="check-nota" style={{ marginBottom: "var(--space-3)" }}>
              {instalado ? motor.descricao : motor.semSuporte}
            </p>

            <div className="grade-3">
              {doMotor.map((m) => (
                <div key={m.nome} className="card blueprint elev-sm" style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", opacity: instalado ? 1 : 0.6 }}>
                  <Canto />
                  <div className="card-kicker">
                    {m.baixado ? `Baixado · ${formatarMB(m.tamanho_disco_mb)}` : `~${m.tamanho_aprox_mb} MB`}
                  </div>
                  <div className="card-title">
                    {m.rotulo}
                    {m.recomendado && <span className="tag tag-accent" style={{ marginLeft: 8 }}>Recomendado</span>}
                    {m.e_padrao && <span className="tag tag-neutral" style={{ marginLeft: 6 }}>Padrão</span>}
                  </div>
                  {/* Idioma em destaque: é o critério que mais elimina modelos
                      para quem transcreve em português. */}
                  <div className="tag tag-outline" style={{ alignSelf: "flex-start" }}>🌐 {m.idiomas}</div>
                  <p className="card-body" style={{ flex: 1 }}>{m.resumo}</p>

                  {!instalado ? (
                    <span className="check-nota">Requer o motor {motor.rotulo}.</span>
                  ) : m.download_status === "baixando" ? (
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
          </div>
        );
      })}
    </>
  );
}

function formatarMB(mb: number | null): string {
  if (mb == null) return "-";
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${Math.round(mb)} MB`;
}
