import { useEffect, useState } from "react";
import { api } from "./api";
import NovaTranscricao from "./paginas/NovaTranscricao";
import Historico from "./paginas/Historico";
import Modelos from "./paginas/Modelos";

type Aba = "nova" | "historico" | "modelos";
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

export default function App() {
  const [aba, setAba] = useState<Aba>("nova");
  const [tema, alternarTema] = usarTema();
  const [online, setOnline] = useState<boolean | null>(null);
  // Chave para forçar recarregar a aba de modelos após uma transcrição, etc.
  const [recarregarModelos, setRecarregarModelos] = useState(0);

  useEffect(() => {
    api.saude().then(setOnline);
  }, []);

  return (
    <div className="app">
      <aside className="barra-lateral">
        <div className="logo">
          <span className="logo-icone">🎬</span>
          <div>
            <div className="logo-texto">Transcritor</div>
            <div className="logo-sub">Vídeos e áudios → texto</div>
          </div>
        </div>

        <button className={`nav-item ${aba === "nova" ? "ativo" : ""}`} onClick={() => setAba("nova")}>
          <span className="icone">✏️</span> Nova transcrição
        </button>
        <button
          className={`nav-item ${aba === "historico" ? "ativo" : ""}`}
          onClick={() => setAba("historico")}
        >
          <span className="icone">🕑</span> Histórico
        </button>
        <button
          className={`nav-item ${aba === "modelos" ? "ativo" : ""}`}
          onClick={() => setAba("modelos")}
        >
          <span className="icone">📦</span> Modelos
        </button>

        <div className="barra-rodape">
          <button className="interruptor" onClick={alternarTema}>
            {tema === "claro" ? "🌙 Tema escuro" : "☀️ Tema claro"}
          </button>
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
            <NovaTranscricao
              aoConcluir={() => setRecarregarModelos((n) => n + 1)}
              irParaModelos={() => setAba("modelos")}
            />
          )}
          {aba === "historico" && <Historico />}
          {aba === "modelos" && <Modelos key={recarregarModelos} />}
        </div>
      </main>
    </div>
  );
}
