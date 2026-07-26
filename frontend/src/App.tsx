import { useEffect, useState } from "react";
import { api } from "./api";
import logo from "./assets/logo.png";
import NovaTranscricao from "./paginas/NovaTranscricao";
import Historico from "./paginas/Historico";
import Modelos from "./paginas/Modelos";
import Dicionarios from "./paginas/Dicionarios";
import Resumir from "./paginas/Resumir";
import Configuracoes from "./paginas/Configuracoes";

type Aba = "nova" | "historico" | "modelos" | "dicionarios" | "resumir" | "configuracoes";
type Tema = "claro" | "escuro";

function usarTema(): [Tema, () => void] {
  const [tema, setTema] = useState<Tema>(() => {
    const salvo = localStorage.getItem("tema") as Tema | null;
    if (salvo) return salvo;
    const prefereEscuro = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
    return prefereEscuro ? "escuro" : "claro";
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-tema", tema);
    localStorage.setItem("tema", tema);
  }, [tema]);
  return [tema, () => setTema((t) => (t === "claro" ? "escuro" : "claro"))];
}

/**
 * Envelope de aba: mantém a tela MONTADA e apenas a esconde quando inativa.
 *
 * Antes, trocar de aba desmontava a tela — e com ela ia embora a transcrição em
 * andamento (formulário, progresso e o WebSocket). Com `display: contents` o
 * envelope não cria caixa nenhuma no layout quando visível, então o visual
 * continua idêntico ao de antes.
 */
function Painel({ ativo, children }: { ativo: boolean; children: React.ReactNode }) {
  return <div style={{ display: ativo ? "contents" : "none" }}>{children}</div>;
}

function ItemNav({
  ativo,
  onClick,
  children,
  icone,
}: {
  ativo: boolean;
  onClick: () => void;
  children: React.ReactNode;
  icone: React.ReactNode;
}) {
  return (
    <button type="button" className={`sidebar-item ${ativo ? "active" : ""}`} onClick={onClick}>
      {icone}
      {children}
    </button>
  );
}

export default function App() {
  const [aba, setAba] = useState<Aba>("nova");
  const [tema, alternarTema] = usarTema();
  const [online, setOnline] = useState<boolean | null>(null);
  const [recarregar, setRecarregar] = useState(0);
  // Telas já abertas alguma vez: ficam montadas para não perder o que está em
  // andamento. As nunca visitadas não são criadas à toa.
  const [visitadas, setVisitadas] = useState<Set<Aba>>(() => new Set<Aba>(["nova"]));

  function irPara(destino: Aba) {
    setVisitadas((atuais) => (atuais.has(destino) ? atuais : new Set(atuais).add(destino)));
    setAba(destino);
  }

  useEffect(() => {
    api.saude().then(setOnline);
  }, []);

  return (
    <div className="app">
      <aside className="barra-lateral">
        <div className="logo">
          <img className="logo-img" src={logo} alt="Transkript.ai" />
          <div className="logo-sub">Vídeos e áudios → texto</div>
        </div>

        <nav className="nav">
          <ItemNav
            ativo={aba === "nova"}
            onClick={() => irPara("nova")}
            icone={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9" />
                <path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z" />
              </svg>
            }
          >
            Nova transcrição
          </ItemNav>
          <ItemNav
            ativo={aba === "historico"}
            onClick={() => irPara("historico")}
            icone={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            }
          >
            Histórico
          </ItemNav>
          <ItemNav
            ativo={aba === "modelos"}
            onClick={() => irPara("modelos")}
            icone={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="m7.5 4.27 9 5.15" />
                <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
                <path d="m3.3 7 8.7 5 8.7-5" />
                <path d="M12 22V12" />
              </svg>
            }
          >
            Modelos
          </ItemNav>
          <ItemNav
            ativo={aba === "dicionarios"}
            onClick={() => irPara("dicionarios")}
            icone={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
              </svg>
            }
          >
            Dicionários
          </ItemNav>
          <ItemNav
            ativo={aba === "resumir"}
            onClick={() => irPara("resumir")}
            icone={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9.5 14.5 3.5 8.5" />
                <path d="m14.5 9.5 6.5 6" />
                <path d="M8.5 9.5l-5 5" />
                <path d="m15.5 14.5 5-5" />
                <path d="m3 3 18 18" />
              </svg>
            }
          >
            Resumir com IA
          </ItemNav>
          <ItemNav
            ativo={aba === "configuracoes"}
            onClick={() => irPara("configuracoes")}
            icone={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            }
          >
            Configurações
          </ItemNav>
        </nav>

        <div className="barra-rodape">
          <button className="interruptor" onClick={alternarTema}>
            {tema === "claro" ? "🌙 Tema escuro" : "☀️ Tema claro"}
          </button>
          <div className="nota-local">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent-700)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <div>100% local. Nenhum áudio ou vídeo sai do seu computador.</div>
          </div>
        </div>
      </aside>

      <main className="conteudo">
        <div className="conteudo-interno">
          {online === false && (
            <div className="alerta alerta-erro">
              <span className="icone">⚠️</span>
              <div>
                Não consegui falar com o servidor do aplicativo. Se você abriu pelo navegador em modo
                de desenvolvimento, verifique se a API está rodando.
              </div>
            </div>
          )}

          {/* Cada tela visitada fica montada e só é escondida — é isso que faz a
              transcrição em andamento sobreviver à troca de abas. */}
          <Painel ativo={aba === "nova"}>
            <NovaTranscricao
              aoConcluir={() => setRecarregar((n) => n + 1)}
              irParaModelos={() => irPara("modelos")}
            />
          </Painel>
          {visitadas.has("historico") && (
            <Painel ativo={aba === "historico"}>
              <Historico sinalRecarregar={recarregar} />
            </Painel>
          )}
          {visitadas.has("modelos") && (
            <Painel ativo={aba === "modelos"}>
              <Modelos sinalRecarregar={recarregar} />
            </Painel>
          )}
          {visitadas.has("dicionarios") && (
            <Painel ativo={aba === "dicionarios"}>
              <Dicionarios />
            </Painel>
          )}
          {visitadas.has("resumir") && (
            <Painel ativo={aba === "resumir"}>
              <Resumir />
            </Painel>
          )}
          {visitadas.has("configuracoes") && (
            <Painel ativo={aba === "configuracoes"}>
              <Configuracoes />
            </Painel>
          )}
        </div>
      </main>
    </div>
  );
}
