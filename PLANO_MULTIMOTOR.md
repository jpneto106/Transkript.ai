# Plano — Suporte a múltiplos motores de transcrição (Whisper + NVIDIA + outros)

Este documento é um **plano de arquitetura** (ainda não implementado) para o app passar a
suportar modelos de transcrição de fornecedores diferentes, além do faster-whisper que já usamos.
Foi escrito a pedido do usuário, que quer "lidar com modelos variados" — incluindo modelos da
NVIDIA e outros do Hugging Face.

## Por que isso é um subsistema novo (e não só "mais um modelo na lista")

Hoje todo o app assume um único motor: `faster-whisper`. Ele carrega um `WhisperModel`, chama
`.transcribe()` e recebe segmentos com timestamps de palavra. Outros motores têm **APIs, formatos
de saída, dependências e requisitos de hardware completamente diferentes**:

| Motor | Biblioteca | Saída nativa | Peso / requisito |
|---|---|---|---|
| Whisper (atual) | `faster-whisper` (CTranslate2) | segmentos + palavras com tempo | já instalado, roda na GPU/CPU |
| NVIDIA Parakeet / Canary | `nemo_toolkit[asr]` (NeMo) | texto + timestamps (formato próprio) | pesado (PyTorch + NeMo), GPU recomendada |
| Whisper "puro" / distil | `transformers` (Hugging Face) | texto + chunks | PyTorch, mais lento que faster-whisper |
| Wav2Vec2 e afins | `transformers` | texto (às vezes sem pontuação) | PyTorch |

Ou seja: cada motor é um "plugin" com seu próprio carregamento, transcrição e conversão de saída
para o nosso formato comum. A boa notícia é que o núcleo do app **já está quase pronto para isso**,
porque a lógica de blocos/escrita/progresso é agnóstica ao motor — ela só precisa receber uma
lista de `Palavra`/`Segmento`.

## Arquitetura proposta: um "adaptador de motor" (interface comum)

Criar uma interface `MotorTranscricao` em `nucleo/motores/` que todo motor implementa:

```python
# nucleo/motores/base.py
class MotorTranscricao(Protocol):
    id: str                 # "whisper", "nemo", "hf-transformers"
    def modelos_disponiveis(self) -> list[InfoModelo]: ...
    def esta_baixado(self, nome: str) -> bool: ...
    def baixar(self, nome: str) -> None: ...
    def remover(self, nome: str) -> None: ...
    def carregar(self, nome: str, dispositivo: str) -> "ModeloCarregado": ...

class ModeloCarregado(Protocol):
    def transcrever(self, arquivo, *, idioma, tarefa, ao_progredir) -> ResultadoBruto: ...
    # ResultadoBruto entrega segmentos/palavras num formato comum, que o nucleo já
    # sabe reagrupar em blocos (montar_blocos) e escrever (escrever_saidas).
```

- `nucleo/motores/whisper.py` — embrulha o que já existe hoje (faster-whisper). É o primeiro e
  serve de referência.
- `nucleo/motores/nemo.py` — NVIDIA NeMo (Parakeet/Canary), adicionado depois.
- `nucleo/motores/transformers.py` — modelos do Hugging Face via `transformers`.

Um **registro** (`nucleo/motores/__init__.py`) lista os motores disponíveis conforme as
dependências instaladas (ex.: se `nemo_toolkit` não estiver instalado, o motor NeMo simplesmente
não aparece — sem quebrar o app).

## Impacto no resto do app (pequeno, graças à separação já feita)

- **API `/api/modelos`**: passa a devolver os modelos **agrupados por motor**, cada um com um campo
  `motor`. Ganha um parâmetro para instalar as dependências de um motor sob demanda (opcional).
- **Banco**: a tabela `transcricoes` ganha uma coluna `motor` (além de `modelo`). A preferência de
  padrão vira `(motor, modelo)`.
- **`api/trabalhos.py`**: em vez de chamar `faster-whisper` direto, pede ao registro o motor certo
  e usa a interface comum. O cache de modelo passa a ser chaveado por `(motor, modelo, dispositivo)`.
- **Frontend**: a aba **Modelos** (já preparada visualmente com um card "Outros motores — em breve")
  passa a mostrar seções por motor (Whisper, NVIDIA, Hugging Face), cada modelo com um selo do
  motor. A tela de Nova transcrição mostra o motor junto do modelo escolhido.

## Requisitos e cuidados

- **Dependências pesadas e opcionais**: NeMo e `transformers` trazem PyTorch e vários pacotes
  grandes. Devem ser **instalados sob demanda** (um botão "Instalar suporte a NVIDIA" que roda o
  `pip install`), não no `requirements` padrão — senão o app fica gigante para quem só quer Whisper.
- **VRAM**: modelos NeMo grandes podem não caber na GPU de 8 GB (RTX 4060 Laptop). Precisamos
  detectar e avisar, com fallback para CPU quando fizer sentido.
- **Timestamps de palavra**: nem todo motor entrega timestamp por palavra (necessário para os
  blocos de legenda atuais). Onde faltar, cair para timestamp por segmento.
- **Licenças/termos**: alguns modelos exigem aceitar termos no Hugging Face (às vezes um token).
  Tratar como no plano de diarização (pedir token quando necessário, explicando o porquê).

## Fases sugeridas (quando formos implementar)

1. **Refatorar para a interface `MotorTranscricao`** com um único motor (Whisper), sem mudar nada
   visível — mesma validação de regressão que fizemos na Fase 1 do projeto.
2. **Agrupar por motor** na API e na aba Modelos (ainda só Whisper), preparando a UI.
3. **Adicionar o motor Hugging Face `transformers`** (mais simples que NeMo, mesmo ecossistema
   PyTorch), com instalação sob demanda.
4. **Adicionar o motor NVIDIA NeMo** (Parakeet/Canary), com detecção de VRAM e instalação sob
   demanda.
5. **Unificar diarização** (do outro plano) como uma etapa pós-transcrição comum a todos os motores.

## Relação com a diarização (identificar falantes)

A diarização (pyannote) é **independente do motor**: ela roda sobre o áudio para descobrir "quem
falou quando", e depois casamos esses intervalos com os segmentos que qualquer motor produziu.
Por isso vale implementá-la como uma etapa separada, reutilizável, depois que a interface de
motores existir.
