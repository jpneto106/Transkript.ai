import { useEffect, useMemo, useRef, useState } from "react";
import { api, pywebview } from "../api";
import { Campo } from "../componentes/Ajuda";
import type { EstadoAoVivo, ModeloInfo, Transcricao } from "../tipos";

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

const FORMATOS_INFO: Record<string, { rotulo: string; dica: string }> = {
  txt: { rotulo: "TXT (texto)", dica: "Texto puro, para ler ou copiar." },
  srt: { rotulo: "SRT (legenda)", dica: "Legenda com tempos, usada na maioria dos players." },
  vtt: { rotulo: "VTT (legenda web)", dica: "Legenda para vídeos na web/HTML5." },
  json: { rotulo: "JSON (dados)", dica: "Dados estruturados com tempos, para uso técnico." },
};

interface Props {
  aoConcluir: () => void;
  irParaModelos: () => void;
}

export default function NovaTranscricao({ aoConcluir, irParaModelos }: Props) {
  const [modelos, setModelos] = useState<ModeloInfo[]>([]);

  const [entrada, setEntrada] = useState("");
  const [nomeArquivo, setNomeArquivo] = useState("");
  const [modelo, setModelo] = useState("small");
  const [idioma, setIdioma] = useState("");
  const [dispositivo, setDispositivo] = useState("auto");
  const [formatos, setFormatos] = useState<string[]>(["txt", "srt"]);
  const [maxCaracteres, setMaxCaracteres] = useState(80);
  const [maxDuracao, setMaxDuracao] = useState(6);
  const [semVad, setSemVad] = useState(false);
  const [mostrarAvancado, setMostrarAvancado] = useState(false);

  const [arrastando, setArrastando] = useState(false);
  const [erro, setErro] = useState("");

  const [estado, setEstado] = useState<EstadoAoVivo | null>(null);
  const [processando, setProcessando] = useState(false);
  const [resultado, setResultado] = useState<Transcricao | null>(null);
  const [textoResultado, setTextoResultado] = useState("");
  const [copiado, setCopiado] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const inputArquivoRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    carregarModelos();
    return () => wsRef.current?.close();
  }, []);

  async function carregarModelos() {
    try {
      const [ms, cfg] = await Promise.all([api.modelos(), api.config()]);
      setModelos(ms);
      const padrao = cfg.modelo_padrao;
      const baixados = ms.filter((m) => m.baixado);
      // Escolhe: padrão (se baixado) → primeiro baixado → padrão mesmo assim.
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
    setFormatos((atual) =>
      atual.includes(f) ? atual.filter((x) => x !== f) : [...atual, f],
    );
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
    if (ehUrl) {
      setNomeArquivo("");
    } else {
      const partes = valor.split(/[\\/]/);
      setNomeArquivo(partes[partes.length - 1] || "");
    }
  }

  function aoSoltar(e: React.DragEvent) {
    e.preventDefault();
    setArrastando(false);
    const arquivo = e.dataTransfer.files?.[0] as (File & { path?: string }) | undefined;
    if (arquivo?.path) {
      definirEntrada(arquivo.path);
    } else if (arquivo) {
      setErro(
        "Não consegui pegar o local desse arquivo pelo arraste. Clique na área para escolher pelo explorador.",
      );
    }
  }

  function aoSelecionarInput(e: React.ChangeEvent<HTMLInputElement>) {
    const arquivo = e.target.files?.[0] as (File & { path?: string }) | undefined;
    if (arquivo?.path) definirEntrada(arquivo.path);
    else if (arquivo)
      setErro(
        "Seu navegador não informa o caminho do arquivo. No aplicativo instalado isso funciona; " +
          "por aqui, cole o caminho ou um link no campo abaixo.",
      );
  }

  async function transcrever() {
    if (!entrada.trim()) {
      setErro("Escolha um arquivo ou cole um link primeiro.");
      return;
    }
    if (formatos.length === 0) {
      setErro("Escolha pelo menos um formato de saída.");
      return;
    }
    setErro("");
    setResultado(null);
    setTextoResultado("");
    setProcessando(true);
    setEstado(null);

    try {
      const { id } = await api.criarTranscricao({
        entrada: entrada.trim(),
        modelo,
        idioma: idioma || null,
        tarefa: "transcribe",
        dispositivo,
        formatos,
        max_caracteres: maxCaracteres,
        max_duracao: maxDuracao,
        vad_filter: !semVad,
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
          if (msg.transcricao.formatos.includes("txt")) {
            try {
              setTextoResultado(await api.textoArquivo(id, "txt"));
            } catch {
              /* ignore */
            }
          }
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

  async function copiarTexto() {
    await navigator.clipboard.writeText(textoResultado);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1800);
  }

  async function abrirPasta() {
    const py = pywebview();
    if (py && resultado) {
      await py.abrir_pasta(resultado.pasta_saida);
    }
  }

  const percentual = estado?.percentual ?? null;
  const temPy = pywebview() !== null;

  const rotuloStatus = useMemo(() => {
    if (!estado) return "Preparando…";
    return estado.rotulo_status;
  }, [estado]);

  return (
    <>
      <h1 className="pagina-titulo">Nova transcrição</h1>
      <p className="pagina-desc">
        Escolha um vídeo ou áudio (ou cole um link) e clique em transcrever. O texto é gerado no seu
        computador, sem enviar nada para a internet.
      </p>

      {!algumBaixado && modelos.length > 0 && (
        <div className="alerta alerta-info">
          <span className="icone">💡</span>
          <div>
            <b>Primeiro uso:</b> você ainda não baixou nenhum modelo de transcrição. Baixe um para
            começar — recomendamos o <b>Small</b> (rápido e com boa qualidade).{" "}
            <button className="btn-fantasma" style={{ marginTop: 8 }} onClick={irParaModelos}>
              📦 Ir para Modelos
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

      {/* ---------------- arquivo ---------------- */}
      <div className="cartao">
        <div className="cartao-titulo">1. Qual arquivo transcrever?</div>
        {!entrada && (
          <>
            <div
              className={`dropzone ${arrastando ? "arrastando" : ""}`}
              onClick={clicarDropzone}
              onDragOver={(e) => {
                e.preventDefault();
                setArrastando(true);
              }}
              onDragLeave={() => setArrastando(false)}
              onDrop={aoSoltar}
            >
              <div className="dropzone-icone">📁</div>
              <div className="dropzone-titulo">Arraste um arquivo aqui ou clique para escolher</div>
              <div className="dropzone-sub">Aceita vídeos (mp4, mkv…) e áudios (mp3, wav…)</div>
            </div>
            <input
              ref={inputArquivoRef}
              type="file"
              style={{ display: "none" }}
              onChange={aoSelecionarInput}
            />
            <div className="separador-ou">ou</div>
            <input
              type="text"
              placeholder="Cole aqui o caminho de um arquivo ou um link (YouTube, etc.)"
              value={entrada}
              onChange={(e) => definirEntrada(e.target.value)}
            />
          </>
        )}
        {entrada && (
          <div className="arquivo-escolhido">
            <span className="icone">✅</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="nome">{nomeArquivo || entrada}</div>
              {nomeArquivo && <div className="caminho">{entrada}</div>}
            </div>
            <button className="btn-fantasma" onClick={() => definirEntrada("")}>
              Trocar
            </button>
          </div>
        )}
      </div>

      {/* ---------------- opções principais ---------------- */}
      <div className="cartao">
        <div className="cartao-titulo">2. Como transcrever?</div>

        <Campo
          rotulo="Modelo (qualidade × velocidade)"
          dica="Modelos maiores entendem melhor a fala, mas demoram mais. Small é um ótimo equilíbrio."
          ajuda={
            modeloSel && !modeloSel.baixado
              ? `Este modelo ainda não está baixado (~${modeloSel.tamanho_aprox_mb} MB) — ele será baixado automaticamente na primeira vez.`
              : undefined
          }
        >
          <select value={modelo} onChange={(e) => setModelo(e.target.value)}>
            {modelos.map((m) => (
              <option key={m.nome} value={m.nome}>
                {m.rotulo} — {m.resumo}
                {m.baixado ? " ✓ baixado" : " (baixar)"}
              </option>
            ))}
          </select>
        </Campo>

        <Campo
          rotulo="Idioma"
          dica="Se você souber o idioma da fala, escolher deixa a transcrição um pouco melhor e mais rápida."
        >
          <select value={idioma} onChange={(e) => setIdioma(e.target.value)}>
            {IDIOMAS.map((i) => (
              <option key={i.valor} value={i.valor}>
                {i.nome}
              </option>
            ))}
          </select>
        </Campo>

        <Campo
          rotulo="Formatos de saída"
          dica="Escolha em quais arquivos salvar. TXT é o texto corrido; SRT/VTT são legendas com tempos."
        >
          <div className="chips">
            {["txt", "srt", "vtt", "json"].map((f) => (
              <button
                key={f}
                className={`chip ${formatos.includes(f) ? "ativo" : ""}`}
                onClick={() => escolherFormato(f)}
                title={FORMATOS_INFO[f].dica}
                type="button"
              >
                {FORMATOS_INFO[f].rotulo}
              </button>
            ))}
          </div>
        </Campo>

        <button className="avancado-toggle" onClick={() => setMostrarAvancado((v) => !v)}>
          {mostrarAvancado ? "▾" : "▸"} Opções avançadas
        </button>

        {mostrarAvancado && (
          <div style={{ marginTop: 16 }}>
            <Campo
              rotulo="Onde processar"
              dica="A GPU (placa de vídeo) é bem mais rápida. Em 'Automático' o programa usa a GPU se houver uma."
            >
              <select value={dispositivo} onChange={(e) => setDispositivo(e.target.value)}>
                <option value="auto">Automático (usa a GPU se possível)</option>
                <option value="cuda">Sempre GPU</option>
                <option value="cpu">Sempre processador (CPU)</option>
              </select>
            </Campo>

            <div className="grade-2">
              <Campo
                rotulo="Máx. de caracteres por bloco"
                dica="Tamanho máximo de cada trecho de texto/legenda. Menor = blocos mais curtos."
              >
                <input
                  type="number"
                  value={maxCaracteres}
                  min={10}
                  max={500}
                  onChange={(e) => setMaxCaracteres(Number(e.target.value))}
                />
              </Campo>
              <Campo
                rotulo="Máx. de segundos por bloco"
                dica="Duração máxima de cada trecho de legenda, em segundos."
              >
                <input
                  type="number"
                  value={maxDuracao}
                  min={1}
                  max={60}
                  step={0.5}
                  onChange={(e) => setMaxDuracao(Number(e.target.value))}
                />
              </Campo>
            </div>

            <label className="campo-rotulo" style={{ cursor: "pointer", marginTop: 6 }}>
              <input
                type="checkbox"
                checked={semVad}
                onChange={(e) => setSemVad(e.target.checked)}
                style={{ width: "auto" }}
              />
              Não pular trechos de silêncio
            </label>
            <div className="campo-ajuda">
              Por padrão o programa pula silêncios. Marque isto se sentir que algum trecho de fala
              está sendo perdido.
            </div>
          </div>
        )}
      </div>

      {/* ---------------- ação / progresso ---------------- */}
      {!resultado && (
        <button
          className="btn btn-primario btn-grande"
          onClick={transcrever}
          disabled={processando || !entrada}
        >
          {processando ? "Transcrevendo…" : "🎙️ Transcrever"}
        </button>
      )}

      {processando && (
        <div className="cartao" style={{ marginTop: 18 }}>
          <div className="cartao-titulo">
            <span className="girando">⏳</span> {rotuloStatus}
          </div>
          <div className={`barra-progresso ${percentual === null ? "indeterminada" : ""}`}>
            <div className="barra-progresso-preenchida" style={{ width: `${percentual ?? 0}%` }} />
          </div>
          <div className="progresso-texto">
            <span>
              {estado?.duracao_total
                ? `${formatarTempo(estado.progresso_segundos)} de ${formatarTempo(estado.duracao_total)}`
                : "Preparando…"}
            </span>
            <span>{percentual !== null ? `${percentual}%` : ""}</span>
          </div>
        </div>
      )}

      {/* ---------------- resultado ---------------- */}
      {resultado && (
        <div className="cartao" style={{ marginTop: 18 }}>
          <div className="resultado-cabecalho">
            <div className="cartao-titulo" style={{ margin: 0 }}>
              <span>✅</span> Transcrição concluída
            </div>
            <button className="btn-fantasma" onClick={() => { setResultado(null); definirEntrada(""); }}>
              Nova transcrição
            </button>
          </div>

          <div className="metadados">
            {resultado.idioma_detectado && (
              <span>
                Idioma: <b>{resultado.idioma_detectado.toUpperCase()}</b>
              </span>
            )}
            {resultado.duracao_audio != null && (
              <span>
                Duração: <b>{formatarTempo(resultado.duracao_audio)}</b>
              </span>
            )}
            {resultado.tempo_processamento != null && (
              <span>
                Processado em: <b>{formatarTempo(resultado.tempo_processamento)}</b>
              </span>
            )}
          </div>

          {textoResultado && <div className="resultado-texto">{textoResultado}</div>}

          <div className="acoes" style={{ marginTop: 14 }}>
            {textoResultado && (
              <button className="btn btn-secundario" onClick={copiarTexto}>
                {copiado ? "✓ Copiado!" : "📋 Copiar texto"}
              </button>
            )}
            {resultado.formatos.map((f) => (
              <a
                key={f}
                className="btn btn-secundario"
                href={api.urlArquivo(resultado.id, f)}
                download
              >
                ⬇️ Baixar {f.toUpperCase()}
              </a>
            ))}
            {temPy && (
              <button className="btn btn-secundario" onClick={abrirPasta}>
                📂 Abrir pasta
              </button>
            )}
          </div>
          <div className="campo-ajuda" style={{ marginTop: 12 }}>
            Arquivos salvos em: <b>{resultado.pasta_saida}</b>
          </div>
        </div>
      )}
    </>
  );
}

function formatarTempo(segundos: number): string {
  const s = Math.max(0, Math.round(segundos));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}
