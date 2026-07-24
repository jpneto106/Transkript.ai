<p align="center">
  <img src="docs/logo.png" alt="Transkript.ai" width="380">
</p>

<h1 align="center">Transkript.ai</h1>

<p align="center">
  <b>Transcritor de vídeos e áudios — 100% local, com interface gráfica.</b><br>
  Transforma fala em texto no seu próprio computador, usando o Whisper da OpenAI
  (via <code>faster-whisper</code>). Nada é enviado para a internet.
</p>

<p align="center">
  <img alt="Licença: MIT" src="https://img.shields.io/badge/licen%C3%A7a-MIT-blue">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-informational">
  <img alt="Interface" src="https://img.shields.io/badge/interface-React%20%2B%20FastAPI-success">
</p>

---

## ✨ O que faz

- **Transcreve vídeos e áudios** (mp4, mkv, mov, mp3, wav, m4a e outros) localmente.
- **Roda na GPU (NVIDIA/CUDA) ou na CPU**, detectando automaticamente o que há disponível.
- **Aceita arquivo do computador ou link** (YouTube etc., via `yt-dlp`).
- **Vários formatos de saída**: `TXT` (texto), `SRT` e `VTT` (legendas com tempo) e `JSON` (dados).
- **Controle do tamanho dos blocos** de legenda (por caracteres e por duração).
- **Interface gráfica** com tema claro/escuro, histórico das transcrições e gerenciador de modelos.
- **Dicionários de termos**: cadastre nomes próprios e jargões para o modelo acertar melhor.
- **Linha de comando** (CLI) para quem preferir automatizar.

> Privacidade: todo o processamento acontece na sua máquina. Seus áudios e vídeos não saem do computador.

---

## 🖥️ Requisitos

- **Windows 10/11** (o app abre numa janela do Microsoft Edge em modo aplicativo).
- **Python 3.11+** (testado em 3.13).
- **Node.js 18+** (apenas para compilar a interface).
- **ffmpeg** disponível no sistema (para ler áudio/vídeo).
- **GPU NVIDIA** é opcional, mas deixa a transcrição bem mais rápida.

---

## 🚀 Instalação (a partir do código)

```bash
# 1) Crie o ambiente Python e instale as dependências
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt

# 2) Compile a interface
cd frontend
npm install
npm run build
cd ..
```

Se for usar GPU NVIDIA no Windows, instale também as bibliotecas CUDA usadas pelo motor:

```bash
venv\Scripts\python.exe -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

---

## ▶️ Como usar

### Interface gráfica
Dê **duplo-clique em `iniciar_app.bat`**. Abre uma janela onde você escolhe o arquivo (ou cola um
link), ajusta as opções (ou usa os padrões) e clica em **Transcrever**. O resultado aparece na tela,
com botões para copiar, baixar e abrir a pasta.

### Linha de comando
```bash
# Um arquivo específico
venv\Scripts\python.exe transcrever.py "C:\caminho\video.mp4" --idioma pt

# Tudo que estiver na pasta "entrada/"
venv\Scripts\python.exe transcrever.py

# De um link
venv\Scripts\python.exe transcrever.py "https://www.youtube.com/watch?v=..." --idioma pt
```
Principais opções: `--modelo` (tiny/base/small/medium/large-v2/large-v3), `--idioma`,
`--formatos txt srt vtt json`, `--max-caracteres`, `--max-duracao`, `--dispositivo` (auto/cpu/cuda).
Rode `transcrever.py --help` para ver todas.

---

## 🧩 Como funciona (arquitetura)

```
  Janela (Microsoft Edge --app)
        │  interface web
  React + TypeScript  (frontend/)
        │  HTTP + WebSocket
  API FastAPI + Uvicorn  (api/)
        │
  Núcleo de transcrição  (nucleo/)  ← compartilhado com a CLI
        │
  faster-whisper → GPU (CUDA) ou CPU
```

- **`nucleo/`** — lógica de transcrição (modelos, blocos de legenda, escrita dos formatos), usada
  tanto pela CLI quanto pela API.
- **`api/`** — servidor FastAPI: transcrição em fila, histórico (SQLite), modelos e dicionários.
- **`frontend/`** — interface React (telas de Nova transcrição, Histórico, Modelos, Dicionários).
- **`iniciar_app.pyw` / `iniciar_app.bat`** — sobem o servidor e abrem a janela.

Documentação detalhada em [`DOCUMENTACAO.md`](DOCUMENTACAO.md) (CLI) e
[`DOCUMENTACAO_APP.md`](DOCUMENTACAO_APP.md) (aplicativo).

---

## 🗺️ Roadmap

- [ ] Instalador `.exe` para Windows (baixar e instalar, sem depender de Python) — como *Release*.
- [ ] Identificação de falantes (diarização).
- [ ] Suporte a outros motores de transcrição (NVIDIA NeMo etc.) — ver [`PLANO_MULTIMOTOR.md`](PLANO_MULTIMOTOR.md).
- [ ] Resumo automático e tradução.

---

## 📄 Licença

Distribuído sob a licença **MIT** — livre para usar, modificar e distribuir. Veja [`LICENSE`](LICENSE).

## 👤 Autor

Feito por **JP.Neto**.
