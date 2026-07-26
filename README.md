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
> | **Arquivo** | `Transkript.ai-3.0.0-instalador.exe` |
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
- **Vários formatos de saída**: `TXT` (texto), `SRT` e `VTT` (legendas com tempo) e `JSON` (dados).
- **Controle do tamanho dos blocos** de legenda (por caracteres e por duração).
- **Interface gráfica** com tema claro/escuro, histórico das transcrições e gerenciador de modelos.
- **Dicionários de termos**: cadastre nomes próprios e jargões para o modelo acertar melhor.
- **Cancele a qualquer momento** e veja a duração do arquivo antes de começar.
- **Linha de comando** (CLI) para quem preferir automatizar.

> Privacidade: todo o processamento acontece na sua máquina. Seus áudios e vídeos não saem do computador.

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

A versão atual é a **3.0.0**. O programa é usável e está publicado, mas segue **em
construção** — o que vem abaixo é o que está planejado, na ordem em que deve acontecer.

### ✅ Pronto

- [x] Instalador `.exe` para Windows (baixar e instalar, sem depender de Python) — como *Release*.
- [x] Identificação de falantes (diarização), com o modelo já embutido no instalador.
- [x] Suporte a outros motores de transcrição — NVIDIA Parakeet e Canary, ao lado do Whisper.
- [x] Dicionários de termos, histórico em SQLite e controle dos blocos de legenda.

### 🔜 Próximos passos

- [ ] **Revisão das legendas com IA local (Ollama).** Uma passada opcional de um modelo
      de linguagem rodando na própria máquina, via [Ollama](https://ollama.com), para
      arrumar pontuação, capitalização e termos que o reconhecimento de fala errou —
      sem que o texto saia do computador. O Ollama seria instalado à parte; o programa
      apenas o detecta e usa se estiver disponível.
- [ ] **Resumo automático da transcrição**, pelo mesmo caminho local do Ollama.
      Desligado por padrão: transcrever nunca dispara o resumo sozinho.
- [ ] **Editor da transcrição**: corrigir o texto e renomear os falantes
      ("Falante 1" → "Ana"), com player sincronizado e linha do tempo por participante.
- [ ] **Mais formatos de saída**: `HTML`, `Word (.docx)` e `PDF`, além dos quatro atuais.
- [ ] **Presets de legenda para redes sociais** — blocos já ajustados para reels,
      shorts e vídeos curtos, sem precisar calcular caracteres e duração na mão.
- [ ] **Instalador menor.** Hoje o pacote é grande por causa das bibliotecas CUDA e do
      ffmpeg embutidos. A ideia é usar um build enxuto do ffmpeg, reduzir o runtime da
      janela e baixar sob demanda só o que cada máquina precisa — quem não tem placa
      NVIDIA não precisaria carregar as bibliotecas dela.
- [ ] **Liberar o modelo da memória** quando o programa fica um tempo parado.
- [ ] **Assinatura digital do instalador** (hoje o Windows mostra *"Editor desconhecido"*).

### 🧭 Mais adiante

- [ ] **Tradução** da transcrição.
- [ ] **Gravar do microfone e transcrever ao vivo**, incluindo o som do sistema. É o
      item mais caro da lista: exige um pipeline de streaming que o programa ainda não
      tem, já que hoje tudo parte de um arquivo com duração conhecida.

### 🚫 Fora do escopo (por decisão)

Coisas que programas parecidos têm e que aqui foram deliberadamente descartadas:

- **Telemetria de uso** — nenhuma, em nenhuma hipótese.
- **Atalho global e deep-link** (`transkript://`) — exigiriam escrever no registro do
  Windows, o que quebraria a promessa de que desinstalar é apagar a pasta.
- **Expor a API do programa para fora da máquina** — provocaria aviso de firewall
  por algo que este público não pediu.

---

## 📄 Licença

Distribuído sob a licença **MIT** — livre para usar, modificar e distribuir. Veja [`LICENSE`](LICENSE).

## 👤 Autor

Feito por **JP.Neto**.
