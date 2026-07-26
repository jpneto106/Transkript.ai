# Histórico de versões

Todas as versões continuam disponíveis na
[página de Releases](https://github.com/jpneto106/Transkript.ai/releases) —
inclusive as antigas, caso alguma máquina se dê melhor com elas.

O número da versão segue o padrão `MAIOR.MENOR.CORREÇÃO`: o primeiro número muda
quando algo grande é reformulado, o segundo quando recursos são acrescentados, e
o terceiro em correções.

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
