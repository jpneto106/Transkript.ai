# Spike do motor Sona — Etapa 2 do plano v4-leve

> **Veredito: PORTÃO REPROVADO.**
> Eliminatória 1 (timestamps por palavra) falhou. Eliminatória 2 (diarização) passou.
>
> Por causa do plano ser explícito ("se 1 ou 2 falhar: parar"), o spike pára aqui
> e voltamos para as alavancas 1, 3 e 4 que não dependem do Sona.

## Resumo executivo

| Pergunta do portão | Resultado | Evidência |
|---|---|---|
| 🔴 1. Sona devolve `timestamp_granularities[]=word`? | ❌ **NÃO** | `VerboseSegment` no OpenAPI tem só `start, end, text, no_speech_prob, [speaker]`. Sem campo `words`. Sem parâmetro `timestamp_granularities` no request body. |
| 🔴 2. Diarização exposta no HTTP? | ✅ **SIM** | `VerboseSegment.speaker` é um integer opcional — diarização sai junto da transcrição quando ativa. |

Como o Sona é pré-1.0, **manter o Whisper/Pyannote atual** é a escolha segura.
A redução de ~2.100 MB que viria com o Sona fica adiada até o **Sona 1.0** ou
até alguém (nós ou upstream) expor timestamps por palavra.

## O que foi feito

| Etapa do checklist | Status |
|---|---|
| 11. Baixar Sona v0.3.5 e registrar sha256 | ✅ `ferramentas/sona/sona.exe` (87 MB, sha256 `3da9a4b83a95a4cda1801d1ecb6e8f88c8d0f88f0b091fa658b9f26e948f621f`) |
| 12. `sona serve --port 0` + handshake da porta pelo stdout | ✅ `"port":49447,"status":"ready"` |
| 13. `GET /openapi.json` | ✅ 8 endpoints documentados |
| 14. 🔴 Timestamps por palavra | ❌ schema `VerboseSegment` não tem `words` |
| 15. 🔴 Diarização HTTP | ✅ campo `speaker` opcional por segmento |
| 16. Medir velocidade RTX 4060 vs faster-whisper atual | ⏸ não chegou — gate reprovou antes |
| 17. Modo CPU | ⏸ não chegou |
| 18. Process Monitor (escrita fora de RAIZ_APP) | ⏸ não chegou |
| 19. Morre junto com Job Object da casca | ✅ confirmado de graça: Sona tem `--exit-with-parent` default `true` — quando o pai (casca) fecha, o Sona fecha junto. Esse é exatamente o comportamento que queremos no plano. |
| 20. Relatório | ✅ este arquivo |

## Endpoints descobertos

```
GET  /health                  → readiness para subir modelo
GET  /ready                   → modelo carregado?
GET  /skill                   → instruções markdown para agentes IA
POST /v1/audio/transcriptions → transcrição (multipart, OpenAI-compatible)
GET  /v1/models               → lista modelos instalados
DEL  /v1/models               → descarrega modelo
POST /v1/models/load          → carrega modelo de path local
POST /v1/models/metadata      → info do modelo (.ggml) antes de carregar
```

Schema de `VerboseSegment`:
```json
{
  "end":           number,
  "no_speech_prob":number,
  "speaker":       integer|null,    <-- diarização por segmento (opcional)
  "start":         number,
  "text":          string
}
```

Sem `words`. Sem `tokens`. Sem granularidade de palavra.

## Por que isso é bloqueador pra gente

`nucleo/blocos.py::montar_blocos` é a peça que o usuário mais sente: blocos de
legenda que respeitam `max_caracteres` e `max_duracao`, quebrando em fim de
frase. Recebe `list[Palavra]` onde `Palavra` carrega `inicio, fim, texto`. Se
o Sona só devolver segmentos inteiros (uma frase vai de 0.0 a 4.7s, sem falar
em qual palavra começa o que), a função perde a melhor qualidade do programa.
Seria um downgrade disfarçado de modernização.

Mesmo com o `speaker` por segmento, **não dá pra saber em qual palavra houve
a troca de falante** — só o segmento inteiro herda o mesmo rótulo. Nossa
diarização atual (pyannote) devolve turnos em granularidade fina; o Sona
entregaria rótulos mais grosseiros.

## O que sobra

Três alavancas independentes do Sona continuam valendo:

| Alavanca | Plano | Status |
|---|---|---|
| 1. Instalador que baixa (bootstrapper) | Etapa 6 | pode começar |
| 3. Casca leve (trim .NET só tranca contra NETSDK1175) | Etapa 3 | tem a parte fácil pronta; a reescrita Rust fica opcional |
| 4. Podar `servidor.spec` (sai `av`, `ctranslate2`, `onnxruntime`, `tokenizers`, `faster_whisper`) | Etapa 5 | pode começar, mas mantém o Parakeet se ainda quisermos ele na v4 |

Mais as funções novas da Etapa 7 (HTML/DOCX/PDF, presets de reel, resumo por
IA) que também não dependem do Sona.

## Sugestão de próximos passos (a confirmar com o usuário)

1. Não criar `nucleo/motores.py::_sona_*` agora — o Sona fica no radar mas
   não entra na v4.
2. Abrir a Etapa 6 (bootstrapper) com a Etapa 5 (podar servidor.spec) na
   ordem inversa do plano — assim o ganho de tamanho vem logo.
3. Manter Whisper + Parakeet como motores da v4.0.0.
4. Reavaliar o Sona quando sair 1.0 (ou quando alguém adicionar `words` ao
   `VerboseSegment`).

## Anexo — referência de comandos

```sh
# Download
curl -L -o sona.exe \
  https://github.com/thewh1teagle/sona/releases/download/v0.3.5/sona-windows-amd64.exe

# Subir (porta automática)
sona.exe serve --port 0
# → stdout: {"commit":"...","port":XXXXX,"status":"ready","version":"v0.3.5"}

# OpenAPI
curl http://127.0.0.1:<porta>/openapi.json

# Doc em markdown para agentes
curl http://127.0.0.1:<porta>/skill

# Verificar que morre junto com o pai (default)
sona.exe serve --port 0    # fecha o shell → Sona morre
```
