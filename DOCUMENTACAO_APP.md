# Documentação — Aplicativo Desktop (interface gráfica)

Além do transcritor de linha de comando (`transcrever.py`, documentado em `DOCUMENTACAO.md`),
o projeto agora tem um **aplicativo com interface gráfica**. Ele abre numa janela do Windows,
com abas para transcrever, ver o histórico e gerenciar os modelos.

---

## 1. Como abrir o aplicativo

**Duplo-clique em `iniciar_app.bat`.**

Uma janela vai abrir depois de alguns segundos (na primeira vez pode demorar um pouco mais,
enquanto o servidor interno sobe). Não aparece nenhum terminal preto.

Se a janela não abrir, veja a seção "Problemas comuns" no fim deste documento.

---

## 2. Como usar (as três abas)

### ✏️ Nova transcrição
1. **Escolha o arquivo**: arraste um vídeo/áudio para a área pontilhada, ou clique nela para
   abrir o explorador do Windows. Também dá para colar um **link** (YouTube etc.) no campo de texto.
2. **Ajuste as opções** (todas já vêm com um bom padrão — você pode só clicar em transcrever):
   - **Modelo**: qualidade × velocidade. "Small" é o recomendado.
   - **Idioma**: deixe em "Detectar automaticamente" ou escolha, se souber.
   - **Formatos de saída**: TXT (texto), SRT/VTT (legenda), JSON (dados). Padrão: TXT + SRT.
   - **Opções avançadas** (recolhidas): onde processar (GPU/CPU) e o tamanho dos blocos de legenda.
3. **Clique em "Transcrever"**. A barra de progresso mostra o andamento em tempo real.
4. Ao terminar, o texto aparece na tela. Você pode **copiar**, **baixar** cada formato ou
   **abrir a pasta** onde os arquivos foram salvos.

### 🕑 Histórico
Lista todas as transcrições já feitas (guardadas mesmo depois de fechar o app). Clique em "Ver"
para reabrir o texto, copiar/baixar de novo, ou "Remover" para apagar do histórico.

### 📦 Modelos
Os modelos são o "cérebro" que reconhece a fala. Aqui você **baixa**, **remove**, vê o **espaço
em disco** ocupado e define qual é o **modelo padrão**. Você só precisa baixar cada modelo uma vez.

---

## 3. Como funciona por dentro (arquitetura)

O app é dividido em três camadas independentes:

```
  Janela nativa (pywebview)          → iniciar_app.pyw
        │  carrega
  Interface web (React + TypeScript)  → frontend/
        │  conversa por HTTP/WebSocket
  API (FastAPI + Uvicorn)              → api/
        │  usa
  Núcleo de transcrição               → nucleo/  (mesmo motor do CLI)
        │
  faster-whisper → GPU (CUDA) ou CPU
```

Vantagem dessa separação: a interface pode evoluir sem mexer no motor, e a mesma API pode, no
futuro, servir outros recursos (resumo, tradução, etc.) sem reescrever o aplicativo.

### O que cada pasta contém

- **`nucleo/`** — a lógica de transcrição, compartilhada entre o CLI e o app (constantes, blocos,
  detecção de GPU, download de URL, escrita de arquivos, o motor `faster-whisper`).
- **`api/`** — o servidor FastAPI:
  - `main.py`: monta o app, registra as rotas e serve o frontend buildado.
  - `bd.py`: banco SQLite com o histórico e as preferências (fica em `dados_app/historico.db`).
  - `trabalhos.py`: a fila de transcrição (um arquivo por vez), o estado ao vivo de cada job e o
    cache do modelo carregado (para não recarregar toda vez).
  - `modelos_cache.py`: consulta/baixa/remove modelos via `huggingface_hub`.
  - `rotas/`: os endpoints (transcrições, modelos, configuração).
- **`frontend/`** — a interface em React + TypeScript.
  - `src/paginas/`: as três telas (NovaTranscricao, Historico, Modelos).
  - `src/api.ts`: o cliente que conversa com a API.
  - `src/estilos.css`: todo o visual, com tema claro e escuro.
  - `dist/`: a versão compilada (gerada por `npm run build`) — é o que o app abre.
- **`iniciar_app.pyw`** — sobe a API numa porta livre, espera ela responder e abre a janela.
- **`iniciar_app.bat`** — o atalho de duplo-clique.

### Onde ficam os arquivos

- **Transcrições geradas**: pasta `saida/` (mesma do CLI).
- **Histórico e preferências**: `dados_app/historico.db`.
- **Vídeos baixados de links**: `entrada/_downloads/`.
- **Modelos baixados**: no cache do Hugging Face (`C:\Users\<você>\.cache\huggingface\hub`).

---

## 4. Para desenvolver / modificar a interface

Instalar as dependências (uma vez):
```
venv\Scripts\pip.exe install -r requirements-api.txt
cd frontend
npm install
```

Rodar em modo de desenvolvimento (recarrega ao editar):
```
# Terminal 1 — API:
venv\Scripts\python.exe -m uvicorn api.main:app --port 8000 --reload
# Terminal 2 — frontend:
cd frontend
npm run dev      # abre em http://localhost:5173
```
Nesse modo o `src/api.ts` aponta automaticamente para a API na porta 8000 (por isso o CORS libera
`localhost:5173`).

Gerar a versão final (que o `iniciar_app.bat` usa):
```
cd frontend
npm run build    # gera frontend/dist/
```

---

## 5. Problemas comuns

- **A janela não abre / erro de "WebView2"**: o app usa o Microsoft Edge WebView2, que já vem no
  Windows 10/11 atualizado. Se faltar, baixe o "Microsoft Edge WebView2 Runtime (Evergreen)" no
  site da Microsoft e instale.
- **Demora para abrir na primeira vez**: normal — o servidor interno precisa subir. As próximas
  aberturas são mais rápidas.
- **A primeira transcrição de um modelo novo demora**: se o modelo escolhido ainda não foi baixado,
  ele é baixado automaticamente antes de transcrever. Baixe pela aba "Modelos" com antecedência
  para evitar a espera.

---

## 6. O que ainda não existe (roadmap)

Estes recursos foram planejados mas ficam para versões futuras (a arquitetura já foi pensada para
recebê-los sem reescrever o app): resumo automático com IA, tradução, identificação de quem fala
(diarização), correção de pontuação, exportação para Word/PDF, e reprodução do áudio sincronizada
com o texto.
