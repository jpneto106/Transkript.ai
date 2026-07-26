# Histórico de versões

Todas as versões continuam disponíveis na
[página de Releases](https://github.com/jpneto106/Transkript.ai/releases) —
inclusive as antigas, caso alguma máquina se dê melhor com elas.

O número da versão segue o padrão `MAIOR.MENOR.CORREÇÃO`: o primeiro número muda
quando algo grande é reformulado, o segundo quando recursos são acrescentados, e
o terceiro em correções.

---

## [4.0.0](https://github.com/jpneto106/Transkript.ai/releases/tag/v4.0.0) — em breve

Trilha `v4-leve` da `v3-melhorias`. Reduz o instalador em ~30% em relação à v3
e traz a maioria das funções de IA e presets do Vibe, sem mexer na
promessa "100% local" da transcrição.

> **Resumo de privacidade:** transcrição continua 100% local (Whisper +
> NVIDIA Parakeet/Canary rodam na sua máquina). O recurso de **Resumo por
> IA** (novidade da v4) é **opt-in** e desligado por padrão; quando você
> ativa e escolhe um provedor de nuvem, o programa envia o texto a
> **só esse provedor** — a chave é sua, fica só no seu computador, e o
> front avisa antes do primeiro envio. Provedores locais (LM Studio,
> Ollama) mantêm o tráfego na sua rede.

### O que entrou na v4.0.0

- **Saída HTML, DOCX e PDF** ao lado de TXT/SRT/VTT/JSON. HTML sai sem
  nenhuma dependência nova; DOCX usa `python-docx`, PDF usa `fpdf2` —
  ambos pure-Python, sem GUI.
- **Resumo por IA** com 7 provedores pré-configurados (LM Studio, Ollama,
  Groq, OpenRouter, Mistral, OpenAI, Anthropic). Página dedicada na coluna
  lateral (ao lado de "Dicionários"). Configuração inline (provedor,
  chave, modelo, estilo, max-tokens) com persistência em
  `dados/configuracoes.json` via `PUT /api/config`. Endpoint
  `POST /api/resumos` chama `nucleo.resumos.cliente.resumir` de verdade.
- **Presets de legenda** para `nucleo/blocos.py`: `padrao`, `longo`,
  `curto`, `reel`, `frase`. O preset `reel` (24 caracteres, 1,4 s por
  bloco) deixa as legendas com cara de Shorts/Reels.
- **Tela de Configurações** no estilo do Vibe: 8 seções agrupadas por
  cabeçalho (Geral, Transcrição, API e agentes, Avançado, Sobre), com
  tema, idioma, modelo padrão, idioma padrão, formatos padrão, preset de
  legenda, links para docs e repositório.
- **fatiamento.py** extraído de `motores.py`: módulo próprio com dois
  modos (silêncio hoje, VAD preparado para Etapa 7). 11 testes novos.
- **ffmpeg win64-lgpl-shared** (BtbN) com sha256 fixado em
  `instalador/FFMPEG_BUILDINFO.txt` e baixador idempotente
  `instalador/baixar_ffmpeg.py`. `AVISOS_DE_TERCEIROS.txt` na raiz.
- **Bootstrapper** (preparado, ativação automática fica para depois):
  `instalador/ASSETS.md` documenta o esquema, `empacotar.py
  --bootstrap` produz o instalador leve (~120 MB, só casca), e o
  buscador PowerShell `instalador/bootstrap_inicial.ps1` funciona em
  máquina sem Python. `iniciar_v4.bat` testa a v4 sem instalar.
- **setup_dev.bat** prepara `venv` + `frontend/dist/` + `casca Debug` num
  comando só (idempotente, pode rodar mais de uma vez).
- **Pillow sai do bundle** (`servidor.spec`): ninguém no projeto
  importa, mas era empacotado por arraste; economiza ~13 MB.

### Cortes e reduções (medidos)

- PIL fora do bundle: **−13 MB**
- Casca .NET com `InvariantGlobalization=true`: **−10 a −15 MB**
- ffmpeg GPL → LGPL: **−260 MB** no instalador; passa a vir em pacote
  separado nos Releases
- Total estimado: instalador completo de **~1.150 MB** (v3) para
  **~700 MB**; instalador bootstrap **~115 MB** + conteúdo baixado

> O alvo dos ~40 MB do instalador do Vibe exigiria reescrita da casca
> em Rust/Win32 (Etapa 3 do plano `ol-um-outro-agente-graceful-oasis.md`)
> ou a integração com o motor Sona, que reprovou no spike (portão
> fechado: sem timestamps por palavra). Está registrado em
> `instalador/SPIKE_SONA.md`.

### O que **não** está na v4 (e o porquê)

- **Transcrição por microfone / áudio do sistema** — exige pipeline de
  streaming WASAPI que o programa não tem. Adiar para v5.
- **Fine-tuning** — pipeline próprio de treino, fora do escopo.
- **Auto-update** — optamos por Releases no GitHub + baixar_componentes.
- **Tradução** — havia como entrada do Vibe mas decidimos não entrar
  (já cobrimos "Resumo por IA" + transcrição multi-idioma).
- **Deep-link / atalho global** — exigiria registro no Windows.

### Detalhes técnicos

- `nucleo/resumos/` (novo pacote, ~570 linhas): catálogo de provedores +
  cliente HTTP com abstração para OpenAI-compat e Anthropic. 22 testes.
- `nucleo/fatiamento.py` (novo): presets de tamanho, módulo isolado
  com API pública `fatiar(amostras, taxa, *, modo, ...)`. 11 testes.
- `api/esquemas.py`: campos extras em `AtualizarConfigRequest` +
  `ResumirRequest` / `ResumoConfigRequest`.
- `api/rotas/resumos.py` (novo): `GET /api/provedores` e
  `POST /api/resumos` com tratamento de erro 502 quando o provedor
  falha.
- `casca/Program.cs`: agora `4.0.0.0`; flag `InvariantGlobalization`
  liga para reduzir DLLs localizadas.
- `empacotar.py` (Etapa 6): flag `--bootstrap` produz o instalador
  pequeno; função `garantir_ffmpeg()` baixa o LGPL se faltar.

### Como testar localmente

```bat
setup_dev.bat            :: prepara venv + frontend + casca Debug
iniciar_v4.bat           :: abre a janela (uso dev)
```

Para gerar o instalador de produção:

```bat
venv\Scripts\python.exe empacotar.py --full
:: ou --bootstrap para o instalador leve
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" instalador\Transkript.ai.iss
```

### Estatísticas desta versão

- **85 testes** passando em ~0,8 s
- **40 módulos** no bundle do frontend (213 KB JS, 14 KB CSS)
- **22 commits** desde a `v3-melhorias` (não publicado, mas registrado)
- **Cobertura de licença de terceiros:** `AVISOS_DE_TERCEIROS.txt`

---

## [3.0.0](https://github.com/jpneto106/Transkript.ai/releases/tag/v3.0.0) — 26/07/2026

Identificação de falantes e um segundo motor de transcrição.

### Novidades

- **Identificar quem fala** (diarização). Marque a opção e a transcrição sai
  separada por pessoa — `Falante 1:`, `Falante 2:` — nos quatro formatos. No TXT
  vira diálogo; no SRT e no VTT o nome entra na legenda; o JSON traz o falante de
  cada trecho. Se você souber quantas pessoas falam, informe: a separação fica
  mais precisa. **O modelo de vozes já vem no instalador**, sem download nem
  cadastro em lugar nenhum.
- **Modelos da NVIDIA** (Parakeet e Canary) ao lado do Whisper. São bem mais
  rápidos e leves — o Parakeet v3 ocupa 640 MB e transcreve 8 minutos de áudio em
  ~36 segundos —, mas entendem menos idiomas. A aba **Modelos** agora mostra, em
  cada modelo, para quais idiomas ele serve.
- **Botão de cancelar** a transcrição em andamento. A parada leva poucos segundos
  e não deixa arquivo pela metade.
- **Duração e tamanho do arquivo** aparecem assim que você o escolhe, para
  conferir que pegou o certo antes de começar um trabalho longo.

### Correções

- Trocar de aba durante uma transcrição **não interrompe mais o trabalho**. Antes,
  ir ao Histórico ou aos Modelos fazia perder o andamento. Downloads de modelo
  também não se perdem mais ao navegar.
- A barra de progresso deixou de ficar parada nos modelos da NVIDIA.

### Detalhes técnicos

- Áudio longo é dividido em trechos de até 120 segundos antes de ir para os
  modelos da NVIDIA, que têm um teto de duração e ficam desproporcionalmente
  lentos bem antes dele. O corte procura uma pausa, mas o limite de duração é
  obrigatório — funciona também em fala contínua, sem silêncio nenhum.
- Os modelos NVIDIA rodam em ONNX (via `onnx-asr`), e não pelo `nemo_toolkit`:
  é uma dependência a menos, mais leve e mais rápida.

---

## [2.0.0](https://github.com/jpneto106/Transkript.ai/releases/tag/v2.0.0) — 25/07/2026

O programa virou um aplicativo instalável de verdade.

### Novidades

- **Instalador `.exe`**: baixe, dê dois cliques e use. Não precisa mais ter Python,
  Node.js nem ffmpeg na máquina — vem tudo dentro. Não pede senha de administrador.
- **Janela própria**, escrita em C# com WebView2. O programa deixou de abrir numa
  janela do Microsoft Edge: agora tem ícone próprio na barra de tarefas e não
  depende de qual navegador você usa.
- **Aceleração NVIDIA embutida**: se houver placa, o programa a usa sozinho.
- **Desinstalação sem resíduo**: o desinstalador pergunta uma vez se deve remover
  também os modelos baixados e o histórico, e não deixa pasta órfã para trás.

### Detalhes técnicos

- O servidor Python passou a ser empacotado com PyInstaller.
- Modelos, banco de dados e saídas ficam na pasta visível do aplicativo — e não
  escondidos dentro do executável, onde o desinstalador não os encontraria.

---

## [1.2.0](https://github.com/jpneto106/Transkript.ai/releases/tag/v1.2.0) — 24/07/2026

Aplicativo portátil e autossuficiente.

### Novidades

- **Tudo dentro da pasta**: modelos, banco de dados e ffmpeg deixaram de depender
  do sistema. Desinstalar era apagar a pasta.
- **Identidade do projeto**: logo, ícone e licença MIT.

### Correções

- **Fim dos travamentos** ao trocar de aba. A interface deixou de usar `pywebview`
  e passou a abrir numa janela do Microsoft Edge em modo aplicativo.
- **Servidor em processo separado**: fechar a janela encerra tudo e libera a
  memória da placa de vídeo, sem deixar processos órfãos.
- Resolvidos a lentidão e os congelamentos causados por varredura de disco e pela
  sincronização do OneDrive.

---

## [1.1.0](https://github.com/jpneto106/Transkript.ai/releases/tag/v1.1.0) — 23/07/2026

- **Dicionários de termos**: cadastre nomes próprios e jargões para o modelo
  acertar palavras específicas do assunto.
- **Visualização com marcações de tempo** no resultado, além do texto corrido.
- Interface redesenhada (estilo *blueprint*).

---

## [1.0.0](https://github.com/jpneto106/Transkript.ai/releases/tag/v1.0.0) — 22/07/2026

Primeira versão com interface gráfica.

- Transcrição local com Whisper (`faster-whisper`), na GPU ou na CPU.
- Telas de nova transcrição, histórico e gerenciamento de modelos.
- Tema claro/escuro, progresso ao vivo e histórico que persiste entre sessões.
- Saídas em TXT, SRT, VTT e JSON.
- Linha de comando (`transcrever.py`) para quem prefere o terminal.
