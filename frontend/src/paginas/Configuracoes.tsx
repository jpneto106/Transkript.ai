import { useEffect, useState } from "react";
import { api } from "../api";
import type { Opcoes } from "../tipos";

const Canto = () => (
  <>
    <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
  </>
);

type Secao =
  | "geral"
  | "privacidade"
  | "transcricao"
  | "modelos"
  | "finetuning"
  | "api"
  | "avancado"
  | "sobre";

// Copiado do nucleo/blocos.py. Mantido em sincronia via este código estar
// dentro de uma função pura; poderia vir da API depois.
const PRESETS_BLOCOS = [
  { chave: "padrao", rotulo: "Padrão", max_caracteres: 80, max_duracao: 4.0 },
  { chave: "longo", rotulo: "Longo", max_caracteres: 90, max_duracao: 5.0 },
  { chave: "curto", rotulo: "Curto", max_caracteres: 50, max_duracao: 2.5 },
  { chave: "reel", rotulo: "Reel", max_caracteres: 24, max_duracao: 1.4 },
  { chave: "frase", rotulo: "Frase", max_caracteres: 120, max_duracao: 7.0 },
];

export default function Configuracoes() {
  const [secao, setSecao] = useState<Secao>("geral");
  const [opcoes, setOpcoes] = useState<Opcoes | null>(null);

  // Tema (local; não passa pelo backend)
  const [tema, setTema] = useState<"claro" | "escuro">(() => {
    const salvo = localStorage.getItem("tema");
    return (salvo === "claro" || salvo === "escuro") ? salvo : "escuro";
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-tema", tema);
    localStorage.setItem("tema", tema);
  }, [tema]);

  // Transcrição
  const [modeloPadrao, setModeloPadrao] = useState<string>("");
  const [idiomaPadrao, setIdiomaPadrao] = useState<string>("auto");
  const [formatosPadrao, setFormatosPadrao] = useState<string[]>(["txt", "srt"]);
  const [presetBlocos, setPresetBlocos] = useState<string>("padrao");
  const [diarizarPorPadrao, setDiarizarPorPadrao] = useState<boolean>(false);

  // UI
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    carregar();
  }, []);

  async function carregar() {
    try {
      const [opcoesResp, configsResp] = await Promise.all([
        api.opcoes(),
        api.config(),
      ]);
      setOpcoes(opcoesResp);

      setModeloPadrao(configsResp.modelo_padrao ?? opcoesResp.modelos[0] ?? "small");
      setIdiomaPadrao(configsResp.idioma_padrao ?? "auto");
      try {
        const fmts = JSON.parse(configsResp.formatos_padrao ?? "[\"txt\",\"srt\"]");
        if (Array.isArray(fmts)) setFormatosPadrao(fmts);
      } catch { /* mantém default */ }
      setPresetBlocos(configsResp.preset_blocos ?? "padrao");
      setDiarizarPorPadrao(configsResp.diarizar_por_padrao === "1");
    } catch (erro) {
      setMsg("Não consegui carregar as configurações. O servidor Python está rodando?");
    }
  }

  async function salvar() {
    setSalvando(true);
    setMsg(null);
    try {
      const payload: Record<string, unknown> = {
        modelo_padrao: modeloPadrao,
        idioma_padrao: idiomaPadrao,
        formatos_padrao: JSON.stringify(formatosPadrao),
        preset_blocos: presetBlocos,
        diarizar_por_padrao: diarizarPorPadrao ? "1" : "0",
      };
      await api.atualizarConfig(payload);
      setMsg("Configurações salvas.");
    } catch (erro: any) {
      setMsg(erro?.message ?? "Falha ao salvar.");
    } finally {
      setSalvando(false);
    }
  }

  // --------------------------------------------- categorias (esquerda)

  const categorias: { grupo: string; chave: Secao; rotulo: string; icone: React.ReactNode }[] = [
    {
      grupo: "GERAL",
      chave: "geral",
      rotulo: "Geral",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
          <path d="M2 12h20" />
        </svg>
      ),
    },
    {
      grupo: "GERAL",
      chave: "privacidade",
      rotulo: "Privacidade",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      ),
    },
    {
      grupo: "TRANSCRIÇÃO",
      chave: "transcricao",
      rotulo: "Transcrição",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 20h9" />
          <path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z" />
        </svg>
      ),
    },
    {
      grupo: "TRANSCRIÇÃO",
      chave: "modelos",
      rotulo: "Selecionar modelo",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="m7.5 4.27 9 5.15" />
          <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
          <path d="m3.3 7 8.7 5 8.7-5" />
          <path d="M12 22V12" />
        </svg>
      ),
    },
    {
      grupo: "TRANSCRIÇÃO",
      chave: "finetuning",
      rotulo: "Fine-tuning",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2v4" />
          <path d="M12 18v4" />
          <path d="m4.93 4.93 2.83 2.83" />
          <path d="m16.24 16.24 2.83 2.83" />
          <path d="M2 12h4" />
          <path d="M18 12h4" />
        </svg>
      ),
    },
    {
      grupo: "AVANÇADO",
      chave: "api",
      rotulo: "API e agentes",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
      ),
    },
    {
      grupo: "AVANÇADO",
      chave: "avancado",
      rotulo: "Avançado",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      ),
    },
    {
      grupo: "SOBRE",
      chave: "sobre",
      rotulo: "Sobre",
      icone: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
      ),
    },
  ];

  // ------------------------------------- conteúdo (direita, por seção)

  function renderGeral() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>Geral</h2>
        <div className="card blueprint elev-sm" style={{ marginBottom: "var(--space-4)" }}>
          <Canto />
          <div className="field" style={{ marginBottom: "var(--space-3)" }}>
            <label>Tema</label>
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <button
                className={`fmt-tag tag ${tema === "claro" ? "tag-accent" : "tag-outline"}`}
                onClick={() => setTema("claro")}
                type="button"
              >
                ☀️ Claro
              </button>
              <button
                className={`fmt-tag tag ${tema === "escuro" ? "tag-accent" : "tag-outline"}`}
                onClick={() => setTema("escuro")}
                type="button"
              >
                🌙 Escuro
              </button>
            </div>
            <div className="check-nota">O tema fica só neste computador (não sincroniza).</div>
          </div>

          <div className="field">
            <label>Idioma da interface</label>
            <select className="input" value="pt-BR" disabled>
              <option value="pt-BR">Português (Brasil)</option>
            </select>
            <div className="check-nota">
              O programa é pt-BR por enquanto. A transcrição aceita qualquer idioma —
              escolha em <strong>Transcrição</strong> abaixo.
            </div>
          </div>
        </div>

        <div className="card blueprint elev-sm">
          <Canto />
          <h3 style={{ marginTop: 0 }}>Sobre o Transkript.ai</h3>
          <p style={{ marginTop: 0 }}>
            <strong>Transkript.ai v4.0</strong> — transcritor de áudio/vídeo 100%
            local, com Whisper e NVIDIA Parakeet/Canary como motores. Licença
            MIT.
          </p>
          <ul style={{ paddingLeft: "1.2em" }}>
            <li>
              <a href="https://github.com/jpneto106/Transkript.ai" target="_blank" rel="noreferrer">
                Repositório no GitHub
              </a>
            </li>
            <li>
              <a href="https://github.com/jpneto106/Transkript.ai/issues" target="_blank" rel="noreferrer">
                Reportar problema
              </a>
            </li>
            <li>
              <a href="https://github.com/jpneto106/Transkript.ai/blob/master/AVISOS_DE_TERCEIROS.txt" target="_blank" rel="noreferrer">
                Avisos de terceiros (licenças de ffmpeg, CUDA, etc.)
              </a>
            </li>
          </ul>
        </div>
      </>
    );
  }

  function renderPrivacidade() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>Privacidade</h2>
        <div className="card blueprint elev-sm">
          <Canto />
          <h3 style={{ marginTop: 0 }}>O que é local</h3>
          <ul>
            <li>
              <strong>Transcrição.</strong> O áudio/vídeo e o texto gerado ficam
              no seu computador. Nenhum dado vai para a internet.
            </li>
            <li>
              <strong>Dicionários de termos, histórico, modelos baixados.</strong>{" "}
              Tudo dentro de <code>dados/</code> ao lado do programa. Apagar a
              pasta remove tudo.
            </li>
            <li>
              <strong>Identificação de falantes (diarização).</strong> Roda
              localmente (pyannote/WhisperX). Nenhum áudio é enviado para fora.
            </li>
          </ul>

          <h3>Resumo por IA — quando desliga, não sai nada</h3>
          <p>
            O recurso de "Resumo por IA" é <strong>opt-in</strong>. Por padrão,
            o programa é 100% local — nenhum texto é enviado para a internet
            por meio dele.
          </p>
          <p>
            Se você ativar e escolher um provedor de nuvem (Groq, OpenAI,
            Anthropic, Mistral, OpenRouter), o programa enviará o texto
            transcrito para a API daquele provedor.{" "}
            <strong>A escolha é sua e fica salva na aba "Resumo por IA"</strong>.
            Para provedores locais (LM Studio, Ollama), mesmo ativado, o
            tráfego fica na sua máquina.
          </p>

          <h3>Downloads de modelos</h3>
          <p>
            Na primeira transcrição, o programa baixa o modelo escolhido do
            Hugging Face (Whisper e Parakeet/Canary são modelos abertos, sem
            rastreamento).
          </p>
        </div>
      </>
    );
  }

  function renderTranscricao() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>Transcrição</h2>
        <div className="card blueprint elev-sm">
          <Canto />
          <div className="field" style={{ marginBottom: "var(--space-3)" }}>
            <label>Modelo padrão</label>
            <select
              className="input"
              value={modeloPadrao}
              onChange={(e) => setModeloPadrao(e.target.value)}
            >
              {(opcoes?.modelos ?? ["tiny", "base", "small", "medium", "large-v3"]).map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <div className="check-nota">
              Pré-selecionado em toda nova transcrição. O download acontece na
              primeira vez que você usa.
            </div>
          </div>

          <div className="field" style={{ marginBottom: "var(--space-3)" }}>
            <label>Idioma padrão</label>
            <select
              className="input"
              value={idiomaPadrao}
              onChange={(e) => setIdiomaPadrao(e.target.value)}
            >
              <option value="auto">Detectar automaticamente</option>
              <option value="pt">Português</option>
              <option value="en">Inglês</option>
              <option value="es">Espanhol</option>
              <option value="fr">Francês</option>
              <option value="de">Alemão</option>
              <option value="it">Italiano</option>
              <option value="ja">Japonês</option>
              <option value="zh">Chinês</option>
            </select>
            <div className="check-nota">
              "Auto" deixa o Whisper detectar. Fixa em um idioma se você
              sempre transcreve o mesmo.
            </div>
          </div>

          <div className="field" style={{ marginBottom: "var(--space-3)" }}>
            <label>Formatos de saída padrão</label>
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              {(opcoes?.formatos ?? ["txt", "srt", "vtt", "json", "html", "docx", "pdf"]).map((f) => {
                const ativo = formatosPadrao.includes(f);
                return (
                  <button
                    key={f}
                    type="button"
                    className={`fmt-tag tag ${ativo ? "tag-accent" : "tag-outline"}`}
                    onClick={() =>
                      setFormatosPadrao((atuais) =>
                        ativo ? atuais.filter((x) => x !== f) : [...atuais, f],
                      )
                    }
                  >
                    {f.toUpperCase()}
                  </button>
                );
              })}
            </div>
            <div className="check-nota">
              DOCX e PDF exigem <code>python-docx</code> e <code>fpdf2</code> no
              venv (já vêm instalados pelo <code>setup_dev.bat</code>).
            </div>
          </div>

          <div className="field" style={{ marginBottom: "var(--space-3)" }}>
            <label>Preset de legenda (tamanho dos blocos)</label>
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              {PRESETS_BLOCOS.map((p) => {
                const ativo = presetBlocos === p.chave;
                return (
                  <button
                    key={p.chave}
                    type="button"
                    className={`fmt-tag tag ${ativo ? "tag-accent" : "tag-outline"}`}
                    onClick={() => setPresetBlocos(p.chave)}
                    title={`${p.max_caracteres} caracteres · ${p.max_duracao}s`}
                  >
                    {p.rotulo} ({p.max_caracteres}c / {p.max_duracao}s)
                  </button>
                );
              })}
            </div>
            <div className="check-nota">
              <strong>Reel</strong> corta blocos curtos para caber em 2 linhas na
              tela de celular.
            </div>
          </div>

          <div className="field">
            <label>
              <input
                type="checkbox"
                checked={diarizarPorPadrao}
                onChange={(e) => setDiarizarPorPadrao(e.target.checked)}
                style={{ marginRight: 6 }}
              />
              Identificar falantes por padrão
            </label>
            <div className="check-nota">
              Adiciona rótulos de "Falante 1", "Falante 2" na transcrição.
              Requer o pacote de diarização estar instalado.
            </div>
          </div>
        </div>
      </>
    );
  }

  function renderModelos() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>Selecionar modelo</h2>
        <p className="pagina-desc">
          A escolha detalhada de modelos, downloads e remoção acontece na aba
          dedicada na coluna à esquerda.
        </p>
        <div className="card blueprint elev-sm">
          <Canto />
          <p>
            Veja <strong>Modelos</strong> na coluna ao lado para baixar, listar
            e remover modelos do Whisper, Parakeet ou Canary. O modelo
            <em> padrão</em> escolhido aqui nesta aba (em{" "}
            <strong>Transcrição</strong>) só vale para novas transcrições
            que você iniciar depois de salvar.
          </p>
          <div className="acoes">
            <a className="btn btn-secondary blueprint" href="#modelos"><Canto />Ir para Modelos</a>
          </div>
        </div>
      </>
    );
  }

  function renderFinetuning() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>Fine-tuning</h2>
        <div className="card blueprint elev-sm">
          <Canto />
          <h3 style={{ marginTop: 0 }}>Em breve</h3>
          <p>
            Fine-tuning de modelos de fala exige um pipeline próprio: coleta e
            preparação de dados, orquestração de treino na GPU, versionamento de
            checkpoints e integração com a fila de transcrição. É um
            projeto sozinho.
          </p>
          <p>
            <strong>Por que não está na v4?</strong> O{" "}
            <code>ol-um-outro-agente-graceful-oasis.md</code> (plano da v4)
            lista fine-tuning{" "}
            <em>explicitamente como fora do escopo</em> da versão. A promessa da
            v4 é chegar ao tamanho do Vibe sem reinventar treinamento.
          </p>
          <p>
            O que a v4 <strong>trouxe</strong> em vez disso:
          </p>
          <ul>
            <li>Diarização local (WhisperX / pyannote) — você pode treinar o
              modelo de diarização à parte e nos enviar se quiser.</li>
            <li>Resumos por IA — o "modelo" é qualquer API compatível com
              OpenAI; se você treinar um LoRA, é só apontar o campo
              <em> Modelo</em> na aba "Resumir" para o endpoint dele.</li>
          </ul>
        </div>
      </>
    );
  }

  function renderApi() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>API e agentes</h2>
        <div className="card blueprint elev-sm">
          <Canto />
          <h3 style={{ marginTop: 0 }}>Endpoint HTTP local</h3>
          <p>
            O Transkript.ai sobe um servidor FastAPI na máquina local; uma
            página do swagger da API vive na própria janela do programa em
            "Sobre → Documentação". Esse endpoint é{" "}
            <strong>apenas local</strong> (127.0.0.1) — não fica exposto à
            internet a menos que você ative um túnel propositalmente.
          </p>

          <h3>Agentes / skills</h3>
          <p>
            O Vibe tem um endpoint <code>/skill</code> que devolve um markdown com
            instruções para agentes de IA externos (Claude Code, Codex,
            Cursor, etc.) que quiserem pilotar o Transkript.ai por HTTP.
            Disponível em:
          </p>
          <p>
            <code>{window.location.origin || "127.0.0.1:8000"}/api/skill</code>
          </p>
        </div>
      </>
    );
  }

  function renderAvancado() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>Avançado</h2>

        <div className="card blueprint elev-sm" style={{ marginBottom: "var(--space-4)" }}>
          <Canto />
          <h3 style={{ marginTop: 0 }}>Pastas</h3>
          <p>
            Tudo o que o programa produz fica dentro da própria pasta do
            aplicativo. Apagar a pasta apaga tudo (modelos, histórico,
            dicionários, saídas). É assim que o desinstalador não deixa
            resíduo.
          </p>
          <ul>
            <li>
              <strong>Pasta do programa:</strong> <code>{opcoes?.pasta_saida ?? "—"}</code>{" "}
              (um nível acima)
            </li>
            <li>
              <strong>Saída das transcrições:</strong> <code>{opcoes?.pasta_saida ?? "—"}</code>
            </li>
            <li>
              <strong>Dados e histórico:</strong> <code>dados/</code>
            </li>
            <li>
              <strong>Modelos baixados:</strong> <code>modelos/</code>
            </li>
          </ul>
        </div>

        <div className="card blueprint elev-sm" style={{ marginBottom: "var(--space-4)" }}>
          <Canto />
          <h3 style={{ marginTop: 0 }}>Atualizações</h3>
          <p>
            O Transkript.ai não tem atualização automática.
            Para atualizar, baixe a versão nova do{" "}
            <a href="https://github.com/jpneto106/Transkript.ai/releases" target="_blank" rel="noreferrer">
              GitHub Releases
            </a>{" "}
            e instale por cima da atual.
          </p>
        </div>

        <div className="card blueprint elev-sm">
          <Canto />
          <h3 style={{ marginTop: 0 }}>Recursos fora do escopo da v4</h3>
          <p>Itens do Vibe que <strong>não</strong> foram trazidos para a v4:</p>
          <ul>
            <li>Transcrição por microfone e áudio do sistema (vai ficar para v5).</li>
            <li>Ditados ao vivo em qualquer lugar do sistema.</li>
            <li>Atalho global e deep-link <code>vibe://</code>.</li>
            <li>Treinamento/fine-tuning de modelos.</li>
            <li>Auto-update.</li>
          </ul>
          <p className="check-nota">
            Têm custo alto e poucos deles combinam com a promessa "100% local"
            do projeto. Quem sentir falta, contribua com PR.
          </p>
        </div>
      </>
    );
  }

  function renderSobre() {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>Sobre</h2>
        <div className="card blueprint elev-sm">
          <Canto />
          <h3 style={{ marginTop: 0 }}>Transkript.ai</h3>
          <p>
            Transcritor de vídeos e áudios <strong>100% local</strong>, com
            interface gráfica. Whisper (faster-whisper) e NVIDIA
            Parakeet/Canary rodam na sua máquina. Nenhum áudio ou vídeo sai
            do seu computador.
          </p>
          <p>
            <strong>Versão:</strong> v4.0.0-alpha (branch <code>v4-leve</code>).<br />
            <strong>Autor:</strong> JP.Neto (Licença MIT).<br />
            <strong>Repositório:</strong>{" "}
            <a href="https://github.com/jpneto106/Transkript.ai" target="_blank" rel="noreferrer">
              github.com/jpneto106/Transkript.ai
            </a>
          </p>

          <h3>Tecnologias</h3>
          <ul>
            <li>Whisper (OpenAI) via <code>faster-whisper</code> — MIT</li>
            <li>NVIDIA Parakeet/Canary via <code>onnx-asr</code> — Apache 2.0</li>
            <li>Diarização pyannote/WhisperX — MIT</li>
            <li>ffmpeg win64-lgpl-shared (BtbN) — LGPL 2.1+</li>
            <li>CUDA runtime (NVIDIA) — CC-BY-4.0</li>
            <li>yt-dlp — Unlicense</li>
            <li>React + Vite (frontend)</li>
            <li>.NET 10 WebView2 (casca C#)</li>
          </ul>

          <h3>Documentação interna</h3>
          <ul>
            <li>
              <a href="https://github.com/jpneto106/Transkript.ai/blob/master/AVISOS_DE_TERCEIROS.txt" target="_blank" rel="noreferrer">
                AVISOS_DE_TERCEIROS.txt
              </a>{" "}
              — licenças de ffmpeg, CUDA, etc.
            </li>
            <li>
              <a href="https://github.com/jpneto106/Transkript.ai/blob/master/instalador/ASSETS.md" target="_blank" rel="noreferrer">
                instalador/ASSETS.md
              </a>{" "}
              — convenção dos pacotes publicados no GitHub Releases
            </li>
            <li>
              <a href="https://github.com/jpneto106/Transkript.ai/blob/master/instalador/SPIKE_SONA.md" target="_blank" rel="noreferrer">
                instalador/SPIKE_SONA.md
              </a>{" "}
              — relatório da Etapa 2 (motor Sona: portão reprovado)
            </li>
          </ul>
        </div>
      </>
    );
  }

  const conteudo = {
    geral: renderGeral(),
    privacidade: renderPrivacidade(),
    transcricao: renderTranscricao(),
    modelos: renderModelos(),
    finetuning: renderFinetuning(),
    api: renderApi(),
    avancado: renderAvancado(),
    sobre: renderSobre(),
  }[secao];

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", marginBottom: "var(--space-3)" }}>
        <h3 style={{ margin: 0 }}>Configurações</h3>
      </div>

      <div
        className="card blueprint elev-sm"
        style={{
          display: "grid",
          gridTemplateColumns: "200px 1fr",
          minHeight: 540,
          padding: 0,
          overflow: "hidden",
        }}
      >
        <Canto />
        {/* Coluna esquerda: categorias agrupadas (igual Vibe) */}
        <nav
          className="configuracoes-nav"
          style={{
            borderRight: "1px solid var(--color-border)",
            padding: "var(--space-3)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-3)",
            overflowY: "auto",
          }}
        >
          {(() => {
            // Agrupa as categorias pelo cabeçalho "grupo", igual layout do Vibe.
            const grupos: { nome: string; itens: typeof categorias }[] = [];
            for (const c of categorias) {
              const ultimo = grupos[grupos.length - 1];
              if (ultimo && ultimo.nome === c.grupo) {
                ultimo.itens.push(c);
              } else {
                grupos.push({ nome: c.grupo, itens: [c] });
              }
            }
            return grupos.map((g) => (
              <div key={g.nome}>
                <p
                  style={{
                    margin: "0 0 var(--space-1) var(--space-2)",
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: "0.12em",
                    color: "var(--color-text-3)",
                  }}
                >
                  {g.nome}
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {g.itens.map((c) => (
                    <button
                      key={c.chave}
                      type="button"
                      className={`sidebar-item ${secao === c.chave ? "active" : ""}`}
                      onClick={() => setSecao(c.chave)}
                      style={{ width: "100%" }}
                    >
                      {c.icone}
                      {c.rotulo}
                    </button>
                  ))}
                </div>
              </div>
            ));
          })()}
        </nav>

        {/* Coluna direita: conteúdo */}
        <div style={{ padding: "var(--space-4) var(--space-5)", overflowY: "auto", maxHeight: "60vh" }}>
          {conteudo}

          {(secao === "transcricao") && (
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="acoes">
                <button className="btn btn-primary blueprint" onClick={salvar} disabled={salvando}>
                  <Canto />
                  {salvando ? "Salvando…" : "Salvar"}
                </button>
              </div>
              {msg && (
                <div className="alerta alerta-info" style={{ marginTop: "var(--space-3)" }}>
                  <span className="icone">ℹ️</span>
                  <div>{msg}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
