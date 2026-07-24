import { useEffect, useRef, useState } from "react";
import { api, pywebview } from "../api";
import { Tooltip } from "../componentes/Ajuda";
import type { Dicionario, EstadoAoVivo, ModeloInfo, Transcricao } from "../tipos";

const IDIOMAS = [
  { valor: "", nome: "Detectar automaticamente" },
  { valor: "pt", nome: "Português" },
  { valor: "en", nome: "Inglês" },
  { valor: "es", nome: "Espanhol" },
  { valor: "fr", nome: "Francês" },
  { valor: "de", nome: "Alemão" },
  { valor: "it", nome: "Italiano" },
  { valor: "ja", nome: "Japonês" },
];

const FORMATOS = [
  { key: "txt", label: "TXT (texto)" },
  { key: "srt", label: "SRT (legenda)" },
  { key: "vtt", label: "VTT (legenda web)" },
  { key: "json", label: "JSON (dados)" },
];

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

interface Props {
  aoConcluir: () => void;
  irParaModelos: () => void;
}

export default function NovaTranscricao({ aoConcluir, irParaModelos }: Props) {
  const [modelos, setModelos] = useState<ModeloInfo[]>([]);
  const [dicionarios, setDicionarios] = useState<Dicionario[]>([]);

  const [entrada, setEntrada] = useState("");
  const [nomeArquivo, setNomeArquivo] = useState("");
  const [modelo, setModelo] = useState("small");
  const [idioma, setIdioma] = useState("");
  const [dispositivo, setDispositivo] = useState("auto");
  const [formatos, setFormatos] = useState<string[]>(["txt", "srt"]);
  const [maxCaracteres, setMaxCaracteres] = useState(80);
  const [maxDuracao, setMaxDuracao] = useState(6);
  const [semVad, setSemVad] = useState(false);
  const [traduzir, setTraduzir] = useState(false);
  const [diarizar, setDiarizar] = useState(false);
  const [dicionarioId, setDicionarioId] = useState("");
  const [avancadoAberto, setAvancadoAberto] = useState(false);

  const [arrastando, setArrastando] = useState(false);
  const [erro, setErro] = useState("");

  const [estado, setEstado] = useState<EstadoAoVivo | null>(null);
  const [processando, setProcessando] = useState(false);
  const [resultado, setResultado] = useState<Transcricao | null>(null);
  const [textoTxt, setTextoTxt] = useState("");
  const [textoSrt, setTextoSrt] = useState("");
  const [vista, setVista] = useState<"texto" | "tempo">("texto");
  const [copiado, setCopiado] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const inputArquivoRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    carregar();
    return () => wsRef.current?.close();
  }, []);

  async function carregar() {
    try {
      const [ms, cfg, dics] = await Promise.all([api.modelos(), api.config(), api.dicionarios()]);
      setModelos(ms);
      setDicionarios(dics);
      const padrao = cfg.modelo_padrao;
      const baixados = ms.filter((m) => m.baixado);
      if (padrao && ms.find((m) => m.nome === padrao)?.baixado) setModelo(padrao);
      else if (baixados[0]) setModelo(baixados[0].nome);
      else if (padrao) setModelo(padrao);
    } catch {
      /* ignore */
    }
  }

  const algumBaixado = modelos.some((m) => m.baixado);
  const modeloSel = modelos.find((m) => m.nome === modelo);

  function escolherFormato(f: string) {
    setFormatos((a) => (a.includes(f) ? a.filter((x) => x !== f) : [...a, f]));
  }

  async function clicarDropzone() {
    const py = pywebview();
    if (py) {
      const caminhos = await py.escolher_arquivo();
      if (caminhos && caminhos.length > 0) definirEntrada(caminhos[0]);
    } else {
      inputArquivoRef.current?.click();
    }
  }

  function definirEntrada(valor: string) {
    setEntrada(valor);
    setResultado(null);
    setErro("");
    const ehUrl = valor.startsWith("http://") || valor.startsWith("https://");
    if (ehUrl) setNomeArquivo("");
    else {
      const partes = valor.split(/[\\/]/);
      setNomeArquivo(partes[partes.length - 1] || "");
    }
  }

  function aoSoltar(e: React.DragEvent) {
    e.preventDefault();
    setArrastando(false);
    const arquivo = e.dataTransfer.files?.[0] as (File & { path?: string }) | undefined;
    if (arquivo?.path) definirEntrada(arquivo.path);
    else if (arquivo)
      setErro("Não consegui pegar o local desse arquivo pelo arraste. Clique na área para escolher pelo explorador.");
  }

  function aoSelecionarInput(e: React.ChangeEvent<HTMLInputElement>) {
    const arquivo = e.target.files?.[0] as (File & { path?: string }) | undefined;
    if (arquivo?.path) definirEntrada(arquivo.path);
    else if (arquivo)
      setErro("Seu navegador não informa o caminho do arquivo. No aplicativo instalado isso funciona; por aqui, cole o caminho ou um link no campo abaixo.");
  }

  async function transcrever() {
    if (!entrada.trim()) return setErro("Escolha um arquivo ou cole um link primeiro.");
    if (formatos.length === 0) return setErro("Escolha pelo menos um formato de saída.");
    setErro("");
    setResultado(null);
    setTextoTxt("");
    setTextoSrt("");
    setVista("texto");
    setProcessando(true);
    setEstado(null);

    try {
      const { id } = await api.criarTranscricao({
        entrada: entrada.trim(),
        modelo,
        idioma: idioma || null,
        tarefa: traduzir ? "translate" : "transcribe",
        dispositivo,
        formatos,
        max_caracteres: maxCaracteres,
        max_duracao: maxDuracao,
        vad_filter: !semVad,
        dicionario_id: dicionarioId || null,
        diarizar,
      });

      const ws = api.wsProgresso(id);
      wsRef.current = ws;
      ws.onmessage = async (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.tipo === "estado") {
          setEstado(msg as EstadoAoVivo);
        } else if (msg.tipo === "concluido") {
          setProcessando(false);
          setResultado(msg.transcricao);
          aoConcluir();
          const fmts: string[] = msg.transcricao.formatos || [];
          if (fmts.includes("txt")) api.textoArquivo(id, "txt").then(setTextoTxt).catch(() => {});
          if (fmts.includes("srt")) api.textoArquivo(id, "srt").then(setTextoSrt).catch(() => {});
          ws.close();
        } else if (msg.tipo === "erro") {
          setProcessando(false);
          setErro(msg.mensagem || "Ocorreu um erro na transcrição.");
          ws.close();
        }
      };
      ws.onerror = () => {
        setProcessando(false);
        setErro("Perdi a conexão com o servidor durante a transcrição.");
      };
    } catch (e) {
      setProcessando(false);
      setErro(e instanceof Error ? e.message : "Erro ao iniciar a transcrição.");
    }
  }

  async function copiar() {
    const txt = vista === "tempo" ? textoSrt : textoTxt;
    await navigator.clipboard.writeText(txt);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1800);
  }

  const percentual = estado?.percentual ?? null;
  const temPy = pywebview() !== null;

  // ---- resultado ----
  if (resultado) {
    const temSrt = resultado.formatos.includes("srt");
    const textoVisivel = vista === "tempo" ? textoSrt : textoTxt;
    return (
      <>
        <div className="cabecalho-resultado">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: 4 }}>
              <h3 style={{ margin: 0 }}>{resultado.nome_arquivo || "Transcrição"}</h3>
              <span className="tag tag-accent">Concluído</span>
            </div>
            <div style={{ fontSize: 13, color: "var(--color-neutral-600)" }}>
              {resultado.duracao_audio != null && `${formatarTempo(resultado.duracao_audio)} · `}
              {resultado.idioma_detectado && `${resultado.idioma_detectado.toUpperCase()} · `}
              Modelo {resultado.modelo}
            </div>
          </div>
          <div className="acoes">
            <button className="btn btn-secondary blueprint" onClick={copiar}>
              <Canto />
              {copiado ? "✓ Copiado" : "Copiar"}
            </button>
            <button className="btn btn-ghost" onClick={() => { setResultado(null); definirEntrada(""); }}>
              Nova transcrição
            </button>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-3)", flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className="seg">
            <button className={`seg-opt ${vista === "texto" ? "ativo" : ""}`} onClick={() => setVista("texto")}>
              Texto
            </button>
            <button
              className={`seg-opt ${vista === "tempo" ? "ativo" : ""}`}
              onClick={() => setVista("tempo")}
              disabled={!temSrt}
              title={temSrt ? "" : "Inclua o formato SRT para ver com marcações de tempo"}
            >
              Com marcações de tempo
            </button>
          </div>
          <div className="acoes">
            {resultado.formatos.map((f) => (
              <a key={f} className="btn btn-secondary blueprint" href={api.urlArquivo(resultado.id, f)} download>
                <Canto />⬇ {f.toUpperCase()}
              </a>
            ))}
            {temPy && (
              <button className="btn btn-secondary blueprint" onClick={() => pywebview()?.abrir_pasta(resultado.pasta_saida)}>
                <Canto />📂 Pasta
              </button>
            )}
          </div>
        </div>

        <div className="card blueprint elev-sm">
          <Canto />
          {vista === "tempo" && !temSrt ? (
            <div className="text-muted">Inclua o formato SRT ao transcrever para ver as marcações de tempo.</div>
          ) : (
            <div className="transcript-box">{textoVisivel || "(sem texto)"}</div>
          )}
        </div>
        <div className="check-nota" style={{ marginTop: "var(--space-3)" }}>
          Arquivos salvos em: <b>{resultado.pasta_saida}</b>
        </div>
      </>
    );
  }

  // ---- processando ----
  if (processando) {
    return (
      <>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-6)" }}>
          <h3 style={{ margin: 0 }}>Transcrevendo…</h3>
        </div>
        <div className="card blueprint elev-sm">
          <Canto />
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontWeight: 500, marginBottom: "var(--space-3)" }}>
            <span className="girando">⏳</span> {estado?.rotulo_status || "Preparando…"} — {nomeArquivo || entrada}
          </div>
          <div className={`progress-track ${percentual === null ? "indeterminada" : ""}`}>
            <div className="progress-fill" style={{ width: `${percentual ?? 0}%` }} />
          </div>
          <div className="progresso-legenda">
            <span>
              {estado?.duracao_total
                ? `${formatarTempo(estado.progresso_segundos)} de ${formatarTempo(estado.duracao_total)}`
                : "Extraindo áudio e gerando texto…"}
            </span>
            <span>{percentual !== null ? `${percentual}%` : ""}</span>
          </div>
        </div>
      </>
    );
  }

  // ---- formulário ----
  return (
    <>
      <p className="pagina-desc">
        Escolha um vídeo ou áudio, ou cole um link, e clique em transcrever. Todo o processamento
        acontece no seu computador — nada é enviado para a internet.
      </p>

      {!algumBaixado && modelos.length > 0 && (
        <div className="alerta alerta-info">
          <span className="icone">💡</span>
          <div>
            <b>Primeiro uso:</b> você ainda não baixou nenhum modelo. Baixe um para começar —
            recomendamos o <b>Small</b>.{" "}
            <button className="btn btn-ghost" style={{ marginTop: 6 }} onClick={irParaModelos}>
              Ir para Modelos →
            </button>
          </div>
        </div>
      )}

      {erro && (
        <div className="alerta alerta-erro">
          <span className="icone">⚠️</span>
          <div>{erro}</div>
        </div>
      )}

      {/* 1. arquivo */}
      <div className="card blueprint elev-sm" style={{ marginBottom: "var(--space-6)" }}>
        <Canto />
        <h5>1. Qual arquivo transcrever?</h5>
        {!entrada && (
          <>
            <div
              className={`dropzone ${arrastando ? "arrastando" : ""}`}
              onClick={clicarDropzone}
              onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
              onDragLeave={() => setArrastando(false)}
              onDrop={aoSoltar}
            >
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent-700)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 13v8" /><path d="m8 17 4-4 4 4" />
                <path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29" />
              </svg>
              <div className="dropzone-titulo">Arraste um arquivo aqui ou clique para escolher</div>
              <div className="dropzone-sub">Aceita vídeos (mp4, mkv, mov...) e áudios (mp3, wav, m4a...)</div>
            </div>
            <input ref={inputArquivoRef} type="file" style={{ display: "none" }} onChange={aoSelecionarInput} />
            <div className="separador-ou">ou</div>
            <input
              className="input"
              placeholder="Cole aqui o link de um vídeo ou áudio (YouTube, etc.)"
              value={entrada}
              onChange={(e) => definirEntrada(e.target.value)}
            />
          </>
        )}
        {entrada && (
          <div className="arquivo-fila">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent-700)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z" /><path d="M14 2v6h6" />
            </svg>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="nome">{nomeArquivo || entrada}</div>
              {nomeArquivo && <div className="caminho">{entrada}</div>}
            </div>
            <button className="btn btn-ghost" onClick={() => definirEntrada("")}>Trocar</button>
          </div>
        )}
      </div>

      {/* 2. como transcrever */}
      <div className="card blueprint elev-sm" style={{ marginBottom: "var(--space-6)" }}>
        <Canto />
        <h5>2. Como transcrever?</h5>

        <div className="grade-2" style={{ marginBottom: "var(--space-4)" }}>
          <div className="field">
            <label>
              Modelo (qualidade × velocidade)
              <Tooltip texto="Modelos maiores entendem melhor a fala, mas demoram mais. Small é um ótimo equilíbrio." />
            </label>
            <select className="input" value={modelo} onChange={(e) => setModelo(e.target.value)}>
              {modelos.map((m) => (
                <option key={m.nome} value={m.nome}>
                  {m.rotulo} — {m.resumo}{m.baixado ? " ✓" : " (baixar)"}
                </option>
              ))}
            </select>
            {modeloSel && !modeloSel.baixado && (
              <div className="check-nota">
                Ainda não baixado (~{modeloSel.tamanho_aprox_mb} MB) — será baixado na primeira vez.
              </div>
            )}
          </div>
          <div className="field">
            <label>
              Idioma do áudio
              <Tooltip texto="Se você souber o idioma, escolher deixa a transcrição um pouco melhor e mais rápida." />
            </label>
            <select className="input" value={idioma} onChange={(e) => setIdioma(e.target.value)}>
              {IDIOMAS.map((i) => (
                <option key={i.valor} value={i.valor}>{i.nome}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="field" style={{ marginBottom: "var(--space-4)" }}>
          <label>
            Formatos de saída
            <Tooltip texto="Em quais arquivos salvar. TXT é o texto corrido; SRT/VTT são legendas com tempos." />
          </label>
          <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
            {FORMATOS.map((f) => (
              <button
                key={f.key}
                type="button"
                className={`fmt-tag tag ${formatos.includes(f.key) ? "tag-accent" : "tag-outline"}`}
                onClick={() => escolherFormato(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {dicionarios.length > 0 && (
          <div className="field" style={{ marginBottom: "var(--space-4)" }}>
            <label>
              Dicionário de termos
              <Tooltip texto="Ajuda o modelo a acertar nomes próprios e palavras específicas do assunto do vídeo." />
            </label>
            <select className="input" value={dicionarioId} onChange={(e) => setDicionarioId(e.target.value)}>
              <option value="">Nenhum</option>
              {dicionarios.map((d) => (
                <option key={d.id} value={d.id}>{d.nome} ({d.termos.length} termos)</option>
              ))}
            </select>
          </div>
        )}

        <button type="button" className="btn btn-ghost" style={{ paddingLeft: 0, fontSize: 13 }} onClick={() => setAvancadoAberto((v) => !v)}>
          {avancadoAberto ? "▾" : "▸"} Opções avançadas
        </button>

        {avancadoAberto && (
          <div style={{ marginTop: "var(--space-3)", paddingTop: "var(--space-3)", borderTop: "1px solid var(--color-divider)" }}>
            <div className="grade-2" style={{ gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
              <div className="field">
                <label>Onde processar<Tooltip texto="A GPU (placa de vídeo) é bem mais rápida. Em 'Automático' usa a GPU se houver." /></label>
                <select className="input" value={dispositivo} onChange={(e) => setDispositivo(e.target.value)}>
                  <option value="auto">Automático (GPU se possível)</option>
                  <option value="cuda">Sempre GPU</option>
                  <option value="cpu">Sempre processador (CPU)</option>
                </select>
              </div>
              <div className="field">
                <label>Máx. por bloco (caracteres / segundos)<Tooltip texto="Tamanho máximo de cada trecho de legenda. Menor = blocos mais curtos." /></label>
                <div style={{ display: "flex", gap: "var(--space-2)" }}>
                  <input className="input" type="number" value={maxCaracteres} min={10} max={500} onChange={(e) => setMaxCaracteres(Number(e.target.value))} />
                  <input className="input" type="number" value={maxDuracao} min={1} max={60} step={0.5} onChange={(e) => setMaxDuracao(Number(e.target.value))} />
                </div>
              </div>
            </div>

            <label className="linha-check">
              <input type="checkbox" checked={diarizar} onChange={(e) => setDiarizar(e.target.checked)} />
              Identificar falantes diferentes <span className="tag tag-neutral">em breve</span>
            </label>
            <div className="check-nota" style={{ marginBottom: "var(--space-3)" }}>
              Detecta quem fala em diálogos. Será ativado numa próxima atualização.
            </div>

            <label className="linha-check">
              <input type="checkbox" checked={traduzir} onChange={(e) => setTraduzir(e.target.checked)} />
              Traduzir para inglês
            </label>
            <div className="check-nota" style={{ marginBottom: "var(--space-3)" }}>
              Em vez de transcrever no idioma original, gera o texto em inglês.
            </div>

            <label className="linha-check">
              <input type="checkbox" checked={semVad} onChange={(e) => setSemVad(e.target.checked)} />
              Não pular trechos de silêncio
            </label>
            <div className="check-nota">
              Por padrão o programa pula silêncios. Marque se sentir que algum trecho de fala está sendo perdido.
            </div>
          </div>
        )}
      </div>

      <button type="button" className="btn btn-primary btn-block blueprint" style={{ fontSize: 16, padding: "var(--space-4)" }} onClick={transcrever} disabled={!entrada}>
        <Canto />
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 19v3" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><rect x="9" y="2" width="6" height="13" rx="3" />
        </svg>
        Transcrever agora
      </button>
    </>
  );
}

function formatarTempo(segundos: number): string {
  const s = Math.max(0, Math.round(segundos));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}
