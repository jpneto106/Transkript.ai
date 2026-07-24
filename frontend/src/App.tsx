import { useEffect, useState } from "react";
import { api } from "./api";
import logo from "./assets/logo.png";
import NovaTranscricao from "./paginas/NovaTranscricao";
import Historico from "./paginas/Historico";
import Modelos from "./paginas/Modelos";
import Dicionarios from "./paginas/Dicionarios";

type Aba = "nova" | "historico" | "modelos" | "dicionarios";
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
            onClick={() => setAba("nova")}
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
            onClick={() => setAba("historico")}
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
            onClick={() => setAba("modelos")}
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
            onClick={() => setAba("dicionarios")}
            icone={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
              </svg>
            }
          >
            Dicionários
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

          {aba === "nova" && (
            <NovaTranscricao aoConcluir={() => setRecarregar((n) => n + 1)} irParaModelos={() => setAba("modelos")} />
          )}
          {aba === "historico" && <Historico />}
          {aba === "modelos" && <Modelos key={recarregar} />}
          {aba === "dicionarios" && <Dicionarios />}
        </div>
      </main>
    </div>
  );
}
