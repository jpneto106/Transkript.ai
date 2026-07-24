import { useEffect, useState } from "react";
import { api, pywebview } from "../api";
import type { Transcricao } from "../tipos";

export default function Historico() {
  const [itens, setItens] = useState<Transcricao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [aberto, setAberto] = useState<string | null>(null);
  const [texto, setTexto] = useState("");

  useEffect(() => {
    carregar();
  }, []);

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

  async function abrir(t: Transcricao) {
    if (aberto === t.id) {
      setAberto(null);
      return;
    }
    setAberto(t.id);
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
    const apagar = confirm(
      `Remover "${t.nome_arquivo}" do histórico?\n\nClique OK para também apagar os arquivos gerados, ou Cancelar para manter tudo.`,
    );
    // OK = apaga arquivos também; Cancelar = não remove nada (mais seguro).
    if (!apagar) return;
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
      <h1 className="pagina-titulo">Histórico</h1>
      <p className="pagina-desc">Todas as transcrições que você já fez ficam guardadas aqui.</p>

      {carregando && <div className="vazio">Carregando…</div>}

      {!carregando && itens.length === 0 && (
        <div className="vazio">
          <div className="vazio-icone">🕑</div>
          Você ainda não fez nenhuma transcrição.
        </div>
      )}

      {itens.map((t) => (
        <div key={t.id}>
          <div className="lista-item">
            <span style={{ fontSize: 22 }}>{t.status === "concluido" ? "📄" : t.status === "erro" ? "⚠️" : "⏳"}</span>
            <div className="principal">
              <div className="titulo">{t.nome_arquivo || t.entrada_original}</div>
              <div className="detalhe">
                {formatarData(t.criado_em)} · {t.modelo}
                {t.idioma_detectado ? ` · ${t.idioma_detectado.toUpperCase()}` : ""}
                {t.duracao_audio != null ? ` · ${formatarTempo(t.duracao_audio)}` : ""}
              </div>
            </div>
            {t.status === "concluido" && <span className="badge badge-sucesso">Concluído</span>}
            {t.status === "erro" && <span className="badge badge-erro">Erro</span>}
            {t.status !== "concluido" && t.status !== "erro" && (
              <span className="badge badge-neutro">Em andamento</span>
            )}
            {t.status === "concluido" && (
              <button className="btn-fantasma" onClick={() => abrir(t)}>
                {aberto === t.id ? "Fechar" : "Ver"}
              </button>
            )}
            <button className="btn-fantasma btn-perigo" onClick={() => remover(t)}>
              Remover
            </button>
          </div>

          {aberto === t.id && (
            <div className="cartao" style={{ marginTop: -4, marginBottom: 14 }}>
              {t.mensagem_erro && <div className="alerta alerta-erro"><span className="icone">⚠️</span><div>{t.mensagem_erro}</div></div>}
              {texto && <div className="resultado-texto">{texto}</div>}
              <div className="acoes" style={{ marginTop: 12 }}>
                {texto && (
                  <button className="btn btn-secundario" onClick={() => navigator.clipboard.writeText(texto)}>
                    📋 Copiar texto
                  </button>
                )}
                {t.formatos.map((f) => (
                  <a key={f} className="btn btn-secundario" href={api.urlArquivo(t.id, f)} download>
                    ⬇️ Baixar {f.toUpperCase()}
                  </a>
                ))}
                {temPy && (
                  <button
                    className="btn btn-secundario"
                    onClick={() => pywebview()?.abrir_pasta(t.pasta_saida)}
                  >
                    📂 Abrir pasta
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </>
  );
}

function formatarData(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
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
