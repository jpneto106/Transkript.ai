# Documentação — `transcrever.py`

Script de linha de comando que transcreve vídeos e áudios usando o **Whisper** da OpenAI,
rodando **localmente** (sem precisar de internet nem de chave de API), através da biblioteca
`faster-whisper`. Gera arquivos de texto (`.txt`), legenda (`.srt`, `.vtt`) e dados estruturados
(`.json`) a partir da fala reconhecida.

---

## 1. Visão geral do pipeline

Quando você roda o script, ele faz isto, em ordem:

1. **Encontra os arquivos** — lê o que você passou (caminho, pasta ou link) e monta a lista de
   vídeos/áudios a processar.
2. **Escolhe o dispositivo** — detecta se há uma GPU NVIDIA disponível (CUDA) e decide se roda
   nela (mais rápido) ou na CPU.
3. **Carrega o modelo Whisper** — baixa (na primeira vez) e carrega os pesos do modelo escolhido
   (`tiny`, `small`, `medium`, etc.) via `faster-whisper`.
4. **Transcreve cada arquivo** — o `faster-whisper` decodifica o áudio (mesmo dentro de um vídeo),
   roda o modelo e devolve o texto reconhecido com o timestamp de **cada palavra**.
5. **Reagrupa as palavras em blocos** — em vez de usar os blocos "crus" que o Whisper devolve
   (que podem ficar longos demais), o script remonta blocos menores e mais legíveis, respeitando
   limites de caracteres e duração que você pode configurar.
6. **Grava os arquivos de saída** — gera `.txt`/`.srt`/`.vtt`/`.json` na pasta de saída.
7. **Mostra um resumo** — tabela final com idioma detectado, duração, tempo de processamento e
   onde cada arquivo foi salvo.

Tudo isso com uma interface de terminal "bonitinha" feita com a biblioteca `rich` (painéis,
tabelas e barra de progresso coloridos).

---

## 2. Estrutura de pastas do projeto

```
Transcrição de audio/
├── transcrever.py         → o script principal (todo o código está aqui)
├── transcrever.bat        → atalho: dá duplo clique ou arraste arquivos em cima dele
├── requirements.txt       → lista de bibliotecas Python necessárias
├── venv/                  → ambiente virtual Python (onde as bibliotecas ficam instaladas)
├── entrada/                → pasta padrão: coloque aqui os vídeos/áudios a transcrever
│   └── _downloads/        → onde ficam os vídeos baixados quando você usa um link (URL)
└── saida/                  → pasta padrão: onde os resultados (.txt, .srt...) são salvos
```

`entrada/` e `saida/` são criadas automaticamente pelo script na primeira vez que você roda,
caso ainda não existam.

---

## 3. Dependências (`requirements.txt`)

| Biblioteca | Para que serve |
|---|---|
| `faster-whisper` | Motor de transcrição — carrega o modelo Whisper e roda o reconhecimento de fala (usa `ctranslate2` por baixo, mais rápido que o Whisper original em PyTorch). |
| `rich` | Deixa a saída do terminal bonita: painéis, tabelas, cores, barra de progresso. |
| `yt-dlp` | Baixa vídeos a partir de links (YouTube e outros sites), usado só quando você passa uma URL em vez de um arquivo local. |

Instaladas dentro da pasta `venv/`, isoladas do resto do sistema.

---

## 4. Seção por seção do código

### 4.1 Ajustes de compatibilidade no Windows (topo do arquivo)

```python
def _registrar_dlls_nvidia(): ...
```
No Windows, as bibliotecas de GPU da NVIDIA (`cuBLAS`, `cuDNN`) instaladas via `pip` ficam
escondidas dentro da pasta do ambiente virtual e o `ctranslate2` não as acha sozinho. Essa função
localiza essas pastas e as adiciona no `PATH` do processo **antes** de qualquer biblioteca de
transcrição ser importada. Sem isso, rodar na GPU falha com um erro de "DLL não encontrada".

Logo em seguida, o script força a saída do terminal para UTF-8, evitando erros ao imprimir
acentos/caracteres especiais no Windows.

### 4.2 Constantes globais

- `EXTENSOES_SUPORTADAS` — quais extensões de arquivo o script reconhece como vídeo/áudio
  válido ao vasculhar uma pasta (mp4, mkv, mp3, wav, etc.).
- `MODELOS_DISPONIVEIS` — os tamanhos de modelo Whisper que podem ser escolhidos.
- `FORMATOS_DISPONIVEIS` — os formatos de saída suportados (`txt`, `srt`, `vtt`, `json`).
- `PASTA_ENTRADA_PADRAO` / `PASTA_SAIDA_PADRAO` — nomes das pastas `entrada/` e `saida/`.
- `FINALIZADORES_DE_FRASE` — pontuação (`.`, `!`, `?`, `…`) usada para decidir um bom lugar para
  cortar um bloco de legenda.

### 4.3 Estruturas de dados (`@dataclass`)

- **`Palavra`** — uma palavra individual reconhecida, com `inicio`, `fim` (em segundos) e `texto`.
  É a unidade mais fina que o Whisper devolve.
- **`Segmento`** — um bloco de texto (várias palavras já agrupadas), também com `inicio`, `fim`
  e `texto`. É o que vira uma "linha" de legenda ou um parágrafo do `.txt`.
- **`ResultadoTranscricao`** — junta tudo sobre um arquivo transcrito: caminho do arquivo, idioma
  detectado, confiança da detecção, duração, lista de `segmentos` e quanto tempo levou para
  processar.

### 4.4 Funções auxiliares de formatação

- `formatar_hms(segundos)` — transforma segundos em `HH:MM:SS` (usado na tabela-resumo).
- `formatar_timestamp_legenda(segundos, separador_ms)` — formata no padrão de legenda
  (`00:00:05,559` para `.srt`, `00:00:05.559` para `.vtt`).

### 4.5 `montar_blocos()` — o controle de tamanho dos blocos

Esta é a função que resolve a preocupação de **blocos não ficarem grandes demais**. Ela recebe a
lista de palavras (cada uma com seu timestamp exato) e vai juntando palavra por palavra num bloco
até que:

- o texto ultrapasse `max_caracteres` (padrão: 80), **ou**
- a duração do bloco ultrapasse `max_duracao` segundos (padrão: 6.0), **ou**
- o bloco já termine em pontuação forte (`.`, `!`, `?`, `…`) e já tenha um tamanho razoável
  (mais de 40% do limite de caracteres) — isso evita blocos artificialmente cortados no meio de
  uma frase quando dá para fechar num ponto final natural.

Quando qualquer uma dessas condições acontece, o bloco atual é fechado e um novo começa. No final,
sobra uma lista de `Segmento`s menores e mais legíveis — usada tanto no `.txt` quanto no `.srt`/`.vtt`.

### 4.6 `extrair_palavras()`

Recebe os segmentos "crus" que vêm direto do `faster-whisper` (que já pede `word_timestamps=True`)
e achata tudo numa lista única de `Palavra`. Se por algum motivo um segmento não tiver palavras
individuais (raro), usa o segmento inteiro como se fosse uma "palavra" só, para não perder texto.

### 4.7 `detectar_dispositivo()`

Decide se a transcrição roda em `cuda` (GPU) ou `cpu`:

- Se você forçar `--dispositivo cpu`, usa CPU e ponto.
- Se for `auto` (padrão) ou `cuda`, tenta importar `ctranslate2` e perguntar quantas GPUs CUDA
  existem. Se achar pelo menos uma, usa GPU; senão, cai para CPU (avisando, se você tinha pedido
  `cuda` explicitamente e não tinha GPU disponível).
- Também decide o `compute_type`: `float16` na GPU (mais rápido, usa a precisão que a GPU faz bem)
  ou `int8` na CPU (mais leve para processador).

### 4.8 `eh_url()` e `baixar_de_url()` — suporte a links

- `eh_url(texto)` — verifica se o que foi passado começa com `http://` ou `https://`.
- `baixar_de_url(url, pasta_destino)` — usa a biblioteca `yt_dlp` para baixar o **áudio** do vídeo
  (pede `bestaudio/best`, ou seja, a melhor faixa de áudio disponível, sem baixar vídeo em alta
  resolução à toa) e salva dentro de `entrada/_downloads/`. Devolve o caminho do arquivo baixado,
  que depois é tratado como qualquer outro arquivo local.

### 4.9 `encontrar_arquivos()`

Recebe a lista de "entradas" (o que você digitou ou arrastou) e resolve cada uma:

- Se for um **link**, baixa com `baixar_de_url()`.
- Se for uma **pasta**, vasculha recursivamente (`rglob`) e pega todo arquivo cuja extensão esteja
  em `EXTENSOES_SUPORTADAS`.
- Se for um **arquivo**, usa direto.
- Se não existir nada com esse nome/caminho, avisa e ignora (sem travar o resto do processamento).

### 4.10 `escrever_saidas()`

Recebe um `ResultadoTranscricao` já pronto e grava os arquivos pedidos em `--formatos`:

- **`.txt`** — cada bloco (já cortado por `montar_blocos`) em uma linha separada.
- **`.srt`** — formato clássico de legenda: número sequencial, intervalo de tempo
  (`00:00:00,000 --> 00:00:05,559`) e o texto do bloco.
- **`.vtt`** — igual ao `.srt`, mas com cabeçalho `WEBVTT` e ponto em vez de vírgula no tempo
  (padrão usado na web/HTML5).
- **`.json`** — estrutura de dados completa (idioma, duração, todos os blocos com seus tempos),
  útil se você quiser processar a transcrição depois em outro programa.

Todos os arquivos usam o mesmo nome do arquivo original (só troca a extensão) e são salvos dentro
da pasta de saída.

### 4.11 `transcrever_arquivo()`

A função que efetivamente chama o Whisper:

1. Chama `modelo.transcribe(...)` pedindo `word_timestamps=True` (para termos o tempo de cada
   palavra, necessário pro `montar_blocos` funcionar).
2. Cria uma barra de progresso (`progress.add_task`) com o total igual à duração do áudio.
3. Conforme os segmentos crus vão chegando (o Whisper processa em streaming), atualiza a barra de
   progresso com o tempo já coberto.
4. No final, achata tudo em palavras (`extrair_palavras`) e remonta os blocos definitivos
   (`montar_blocos`), guardando também quanto tempo o processamento levou.

### 4.12 `montar_argumentos()` — as opções de linha de comando

Define tudo que pode ser digitado depois de `transcrever.py`. Veja a tabela completa na seção 5.

### 4.13 `main()` — a função que amarra tudo

1. Mostra o painel de título.
2. Decide de onde vêm os arquivos: se você não passou nada, usa a pasta `entrada/` (criando-a se
   não existir); senão, usa o que foi passado.
3. Chama `encontrar_arquivos()`; se não achar nada, mostra uma mensagem explicando o que fazer e
   encerra.
4. Detecta o dispositivo (GPU/CPU) e mostra uma tabela de configuração (pasta de entrada, pasta de
   saída, modelo, dispositivo, idioma, formatos, limite de blocos, quantos arquivos foram achados).
5. Carrega o modelo Whisper (com um spinner de "carregando").
6. Para cada arquivo encontrado: transcreve, grava as saídas e adiciona uma linha na tabela-resumo.
7. No final, imprime a tabela-resumo completa e onde tudo foi salvo.

---

## 5. Opções de linha de comando

| Opção | Padrão | O que faz |
|---|---|---|
| `entradas` (posicional) | pasta `entrada/` | Arquivo(s), pasta(s) ou link(s) a transcrever. Pode passar vários de uma vez. |
| `--modelo`, `-m` | `medium` | Tamanho do modelo: `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`. Maior = mais preciso, porém mais lento e mais pesado para baixar/rodar. |
| `--idioma`, `-l` | detecção automática | Código do idioma (`pt`, `en`, etc.). Se souber o idioma, especificar deixa a transcrição um pouco mais rápida e confiável. |
| `--tarefa` | `transcribe` | `transcribe` mantém o idioma original; `translate` traduz a fala para **inglês**. |
| `--dispositivo`, `-d` | `auto` | `auto` (detecta GPU sozinho), `cpu` ou `cuda` (força GPU). |
| `--saida`, `-o` | `saida` | Pasta onde salvar os resultados. |
| `--formatos`, `-f` | `txt srt` | Quais arquivos gerar: `txt`, `srt`, `vtt`, `json` (pode pedir vários juntos). |
| `--beam-size` | `5` | Parâmetro técnico do algoritmo de decodificação do Whisper (busca em feixe). Valores maiores podem melhorar um pouco a qualidade, à custa de mais tempo de processamento. |
| `--sem-vad` | (desligado) | Desativa o filtro de detecção de voz (VAD). Por padrão, o script pula trechos de silêncio; use essa opção se estiver perdendo trechos de fala que o VAD confunde com silêncio. |
| `--max-caracteres` | `80` | Máximo de caracteres em cada bloco de texto/legenda. |
| `--max-duracao` | `6.0` | Máximo de segundos que cada bloco de texto/legenda pode durar. |

### Exemplos

Transcrever um arquivo específico, detectando idioma sozinho:
```
.\venv\Scripts\python.exe transcrever.py "C:\videos\aula.mp4"
```

Forçando português e gerando os 4 formatos:
```
.\venv\Scripts\python.exe transcrever.py "C:\videos\aula.mp4" --idioma pt --formatos txt srt vtt json
```

Processando tudo que estiver na pasta `entrada/`, com blocos de legenda mais curtos:
```
.\venv\Scripts\python.exe transcrever.py --max-caracteres 40 --max-duracao 4
```

Transcrevendo direto de um link:
```
.\venv\Scripts\python.exe transcrever.py "https://www.youtube.com/watch?v=XXXXXXXXX" --idioma pt
```

---

## 6. Problema conhecido já resolvido: DLL da NVIDIA

Ao instalar `faster-whisper` num Windows sem o CUDA Toolkit completo instalado, rodar na GPU falha
com `RuntimeError: Library cublas64_12.dll is not found or cannot be loaded`. A correção aplicada
foi instalar os pacotes `nvidia-cublas-cu12` e `nvidia-cudnn-cu12` via `pip` (que trazem só as DLLs
necessárias, sem precisar instalar o CUDA Toolkit inteiro) e, na função `_registrar_dlls_nvidia()`,
adicionar as pastas onde essas DLLs ficam ao `PATH` do processo antes de importar qualquer coisa
relacionada ao Whisper. Isso já está resolvido e não exige nenhuma ação manual — é só rodar o
script normalmente.

---

## 7. O que NÃO está implementado (ainda)

- Interface gráfica (por enquanto é só linha de comando / `.bat`).
- Escolha de voz/locutor (diarização — "quem falou o quê").
- Edição da transcrição depois de pronta.

Esses ficam para uma próxima etapa, se fizerem sentido.
