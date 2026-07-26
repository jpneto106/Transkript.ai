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

<p align="center">
  <a href="https://github.com/jpneto106/Transkript.ai/releases/latest">
    <img alt="Baixar para Windows" src="https://img.shields.io/badge/⬇%20Baixar%20para%20Windows-instalador%20.exe-2ea44f?style=for-the-badge&logo=windows&logoColor=white">
  </a>
</p>

---

> ## 💾 Instalar no Windows
>
> **Baixe o instalador, dê dois cliques e pronto.** Não precisa ter Python, Node.js
> nem ffmpeg na máquina — vem tudo dentro do pacote.
>
> | | |
> |---|---|
> | **Arquivo** | `Transkript.ai-4.0.0-instalador.exe` |
> | **Sistema** | Windows 10 ou 11 (64 bits) |
> | **Administrador** | Não pede senha — instala na sua pasta de usuário |
> | **Placa de vídeo** | NVIDIA acelera bastante, mas é opcional (sem ela, roda no processador) |
> | **Desinstalar** | *Configurações → Aplicativos → Transkript.ai* — sai sem deixar resíduo |
>
> ### ➡️ **[Baixar a versão mais recente](https://github.com/jpneto106/Transkript.ai/releases/latest)**
>
> <sub>Todas as versões anteriores continuam disponíveis em
> **[Releases](https://github.com/jpneto106/Transkript.ai/releases)**, e o que mudou
> em cada uma está no **[CHANGELOG](CHANGELOG.md)**.</sub>
>
> <sub>O Windows pode mostrar um aviso de *"Editor desconhecido"* — o instalador não é
> assinado digitalmente. Clique em **Mais informações → Executar assim mesmo**.</sub>

---

## ✨ O que faz

- **Transcreve vídeos e áudios** (mp4, mkv, mov, mp3, wav, m4a e outros) localmente.
- **Identifica quem fala** em diálogos, separando o texto por falante.
- **Dois motores de transcrição**: Whisper (qualquer idioma) e NVIDIA
  Parakeet/Canary (mais rápidos e leves, com menos idiomas).
- **Roda na GPU (NVIDIA/CUDA) ou na CPU**, detectando automaticamente o que há disponível.
- **Aceita arquivo do computador ou link** (YouTube etc., via `yt-dlp`).
- **Vários formatos de saída**: `TXT`, `SRT`, `VTT`, `JSON`, `HTML`, `DOCX`
  e `PDF` (HTML sai sem dependência nova; DOCX/PDF precisam de
  `python-docx`/`fpdf2`, já inclusos no instalador).
- **Presets de legenda** (padrão, longo, curto, **reel** para vídeos
  curtos, frase) com quebra em fim de frase.
- **Resumo por IA** (opt-in, desligado por padrão): LM Studio, Ollama,
  Groq, OpenRouter, Mistral, OpenAI e Claude. A chave fica só no seu
  computador.
- **Interface gráfica** com tema claro/escuro, histórico das
  transcrições, gerenciador de modelos, dicionários de termos, presets
  de legenda, resumo por IA e tela de configurações.
- **Dicionários de termos**: cadastre nomes próprios e jargões para o
  modelo acertar melhor.
- **Cancele a qualquer momento** e veja a duração do arquivo antes de
  começar.
- **Linha de comando** (CLI) para quem preferir automatizar.

> **Privacidade (v4):** a transcrição é 100% local — áudio, vídeo e texto
> ficam na sua máquina. A função de **Resumo por IA** é opt-in e desligada
> por padrão; quando ativada e você escolhe um provedor de nuvem, o
> programa envia o texto só para esse provedor, com a sua chave. Provedores
> locais (LM Studio, Ollama) mantêm o tráfego na sua rede. Detalhes em
> `AVISOS_DE_TERCEIROS.txt`.

---

## 🖥️ Requisitos

**Usando o instalador (`.exe`)** — só isto:

- **Windows 10 ou 11**, 64 bits.
- **GPU NVIDIA** é opcional, mas deixa a transcrição bem mais rápida.

Python, Node.js, ffmpeg e as bibliotecas CUDA já vão dentro do pacote.

**Rodando a partir do código** — além do acima:

- **Python 3.11+** (testado em 3.13) e **Node.js 18+** (para compilar a interface).
- **ffmpeg** no sistema (ex.: `winget install Gyan.FFmpeg`) ou embutido em `ferramentas/ffmpeg`.
- **.NET SDK 10** e **Inno Setup 6**, apenas se você for gerar o instalador.

### Modelo de diarização (identificação de falantes)

O `pyannote/speaker-diarization-community-1` (~32 MB) é **gated** no
Hugging Face — o instalador da v3 o embute em `modelos/hub/`, e o
`empacotar.py` faz o mesmo. No **dev mode** (você rodando `setup_dev.bat`),
o modelo não vem no repo (está em `modelos/`, que é gitignored).

Três caminhos para resolver:

- **Mais fácil (recomendado):** copie o modelo do seu v3 instalado.
  Se você já tem a v3 funcionando, o modelo está em
  `<raiz-do-v3>/modelos/hub/models--pyannote--speaker-diarization-community-1/`.
  Copie essa pasta inteira para
  `modelos/hub/models--pyannote--speaker-diarization-community-1/` na
  raiz deste projeto.
- **Sem v3:** aceite os termos do modelo em
  <https://huggingface.co/pyannote/speaker-diarization-community-1> e
  (opcional) crie um token em <https://huggingface.co/settings/tokens>.
  Defina `HF_TOKEN=hf_…` no ambiente. Na primeira vez que você
  transcrever com "Identificar falantes" marcado, o programa baixa
  o modelo sozinho.
- **Sem internet / sem conta:** peça a um amigo que tenha o
  modelo para te passar os 32 MB.

Sem o modelo, o programa **não quebra** — só a opção de
identificar falantes fica desabilitada.

---

## 🚀 Instalação (a partir do código)

```bash
# 1) Crie o ambiente Python e instale as dependências
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-api.txt -r requirements-extras.txt

# 2) Compile a interface
cd frontend
npm install
npm run build
cd ..
```

**O que vem em cada arquivo de requisitos:**

- `requirements.txt` — Whisper (`faster-whisper`), rich, yt-dlp
- `requirements-api.txt` — FastAPI, Uvicorn, python-docx, fpdf2, e as
  bibliotecas CUDA 12 (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`) que
  o onnxruntime precisa para rodar Parakeet/Canary. Sem GPU, esses
  pacotes ficam instalados mas inativos.
- `requirements-extras.txt` — `pyannote.audio` (traz PyTorch junto) para
  **identificação de falantes**. É opcional: quem só quer transcrever
  com Whisper pode pular.

Se você não quer diarização, basta não instalar o `extras`. Se você
estiver no Linux/macOS e for usar GPU NVIDIA, instale o CUDA Toolkit
correspondente do site da NVIDIA.

---

## ▶️ Como usar

### Interface gráfica
Instalado pelo `.exe`, abra **Transkript.ai** pelo menu Iniciar ou pelo atalho da área de trabalho.
Rodando a partir do código, dê **duplo-clique em `iniciar_app.bat`**.

Abre uma janela onde você escolhe o arquivo (ou cola um link), ajusta as opções (ou usa os padrões)
e clica em **Transcrever**. O resultado aparece na tela, com botões para copiar, baixar e abrir a
pasta. Na primeira transcrição o modelo escolhido é baixado — depois disso funciona sem internet.

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
  Janela nativa em C# (WebView2)  (casca/)
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
- **`casca/`** — janela nativa (C# + WebView2) que sobe o servidor e mostra a interface.
- **`empacotar.py` / `servidor.spec` / `instalador/`** — geram a pasta final e o instalador `.exe`.
- **`iniciar_app.pyw` / `iniciar_app.bat`** — modo desenvolvimento: sobem o servidor a partir do código.

Documentação detalhada em [`DOCUMENTACAO.md`](DOCUMENTACAO.md) (CLI) e
[`DOCUMENTACAO_APP.md`](DOCUMENTACAO_APP.md) (aplicativo).

---

## 📦 Desinstalação

O aplicativo é **autossuficiente**: tudo — programa, modelos, dados, ffmpeg e as bibliotecas
CUDA — fica dentro de uma única pasta. Não espalha arquivos pelo sistema.

- **Instalado pelo `.exe`:** *Configurações → Aplicativos → Transkript.ai → Desinstalar*. O
  desinstalador pergunta se você quer apagar também os modelos baixados e o histórico.
- **Rodando a partir do código:** basta apagar a pasta.

Detalhes em [`COMO_DESINSTALAR.txt`](COMO_DESINSTALAR.txt).

---

## 🗺️ Roadmap

- [x] Instalador `.exe` para Windows (baixar e instalar, sem depender de Python) — como *Release*.
- [x] Identificação de falantes (diarização), com o modelo já embutido no instalador.
- [x] Suporte a outros motores de transcrição — NVIDIA Parakeet e Canary, ao lado do Whisper.
- [x] Saídas HTML, DOCX e PDF (v4).
- [x] Presets de legenda (padrão, longo, curto, **reel**, frase) (v4).
- [x] Resumo por IA com 7 provedores — opt-in, desligado por padrão (v4).
- [ ] Editor da transcrição: corrigir o texto e renomear os falantes ("Falante 1" → "Ana"),
      com player sincronizado e linha do tempo por participante.
- [ ] Assinatura digital do instalador (hoje o Windows mostra *"Editor desconhecido"*).

---

## 📄 Licença

Distribuído sob a licença **MIT** — livre para usar, modificar e distribuir. Veja [`LICENSE`](LICENSE).

## 👤 Autor

Feito por **JP.Neto**.

**Assistentes de IA que participaram do desenvolvimento:**

- **DeepSeek V4 Pro** — responsável pela maior parte da **versão 4**
  (diarização com GPU, Resumo por IA multi-provedor, presets de
  legenda, tela de Configurações, bootstrapper do instalador). Atuou
  como par de programação durante toda a etapa 7 do plano.
- **Claude Code** (Anthropic) — colaborou nas versões 2 e 3
  (instalador .exe, identificação de falantes, motor NVIDIA).

O código-fonte e as decisões de arquitetura são do autor humano;
as IAs aceleraram depuração, refatoração e geração de testes.

---

## 📜 Avisos de terceiros

O Transkript.ai redistribui binários e modelos de terceiros (ffmpeg LGPL,
bibliotecas CUDA NVIDIA CC-BY-4.0, modelos Whisper / Parakeet / pyannote, etc.).
A lista completa, com licenças e fonte de cada peça, está em
[`AVISOS_DE_TERCEIROS.txt`](AVISOS_DE_TERCEIROS.txt).

> **Atribuições obrigatórias** (resumo):
>
> - NVIDIA cuBLAS/cuDNN e modelos Parakeet/Canary são distribuídos sob
>   **CC-BY-4.0**. Aviso: *"This software includes components distributed by
>   NVIDIA Corporation under the Creative Commons Attribution 4.0 license."*
> - **ffmpeg** é distribuído sob **LGPL 2.1+**; binários vêm do build
>   win64-lgpl-shared mantido por BtbN.
