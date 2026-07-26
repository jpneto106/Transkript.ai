# Histórico de versões

Todas as versões continuam disponíveis na
[página de Releases](https://github.com/jpneto106/Transkript.ai/releases) —
inclusive as antigas, caso alguma máquina se dê melhor com elas.

O número da versão segue o padrão `MAIOR.MENOR.CORREÇÃO`: o primeiro número muda
quando algo grande é reformulado, o segundo quando recursos são acrescentados, e
o terceiro em correções.

---

## [4.0.0-alpha.1](https://github.com/jpneto106/Transkript.ai/tree/v4-leve) — em desenvolvimento

Trilha `v4-leve` derivada da `v3-melhorias`. A versão tem dois eixos de trabalho
— **enxugar o instalador** para chegar perto do tamanho do Vibe sem perder
recursos, e **portar features do Vibe** (HTML, presets de legenda para reels,
DOCX, PDF, resumo por IA). Esta primeira alpha só entrega o primeiro eixo,
fase 0 do plano (`ol-um-outro-agente-graceful-oasis.md`).

### Mudanças já aplicadas (fase 0)

- **`servidor.spec`: Pillow (PIL) sai do pacote empacotado.** Nenhuma parte do
  projeto importa `PIL` diretamente, mas a biblioteca chegava ao bundle por
  arraste transitivo. Tirar ela economiza ~13 MB do instalador.
- **`ffmpeg`: troca do build GPL para um build LGPL-only** (BtbN
  / FFmpeg-Builds, asset `ffmpeg-master-latest-win64-lgpl-shared.zip`).
  O hash esperado está fixado em `instalador/FFMPEG_BUILDINFO.txt` e é
  conferido a cada download por `instalador/baixar_ffmpeg.py`. O
  `empacotar.py` chama o baixador automaticamente quando os binários
  ainda não estão em `ferramentas/ffmpeg/bin/`.
- **`AVISOS_DE_TERCEIROS.txt`** adicionado na raiz, listando licenças de
  ffmpeg (LGPL), CUDA (CC-BY-4.0), Whisper/Parakeet/Canary/pyannote e os
  binários do WebView2, com links de origem para quem quiser conferir.
- **README** ganhou a seção "📜 Avisos de terceiros" com as atribuições
  obrigatórias resumidas.
- **Casca (`.csproj`)**: `InvariantGlobalization=true` para reforçar que o
  programa é pt-BR fixo (já tínhamos `SatelliteResourceLanguages=pt-BR`;
  globalization desligada por completo tira ~10–15 MB do runtime do .NET).
  Bump da `AssemblyVersion` para `4.0.0.0`.

### O que NÃO mudou (ainda)

- A interface do Transkript.ai (coluna lateral, tema claro/escuro, as quatro
  abas) **fica intocada** — é o que diferencia este projeto do Vibe e
  continua sendo o nosso padrão.
- Dicionários de termos, histórico SQLite, controle de blocos de legenda,
  dois motores de transcrição (Whisper + Parakeet/Canary).
- Nenhuma `ferramenta/cuda/` foi tocada. As DLLs da NVIDIA continuam
  indo para o instalador; passam a ser download opcional quando o motor
  Sona entrar em cena (Etapas 2 e 4 do plano).

### O que está barrado e por quê

- **Trimming completo do .NET na casca**: o .NET 10 ainda não suporta
  Windows Forms + trim (NETSDK1175). A redução de ~111 MB para ~40 MB que
  o plano previa para esta fase só virá com a reescrita em Rust/Win32
  prevista na Etapa 3 do plano, ou substituindo WinForms por WPF/Avalonia
  em uma versão futura.

### Próximas fases (do plano)

| Etapa | O que | Status |
|---|---|---|
| 1 | `nucleo/fatiamento.py` (VAD do Vibe) | não começou |
| 2 | Spike do motor Sona — **portão de decisão** | não começou |
| 3 | Reescrita da casca em Rust/Win32 (opcional) | não começou |
| 4 | Sona como motor, CUDA vira download opcional | depende de 2 |
| 5 | Podar `servidor.spec` (sai `av`, `ctranslate2`, `onnxruntime`, `tokenizers`, `faster_whisper`) | depende de 4 |
| 6 | Instalador bootstrapper (baixa o que falta dos Releases do GitHub) | depende de 3–5 |
| 7 | HTML, DOCX, PDF, presets de reel, resumo por IA (Ollama local + Claude/OpenAI na nuvem) | não começou |

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
