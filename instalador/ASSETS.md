# Pacotes publicáveis (Assets de Release) — Transkript.ai v4

> A Etapa 6 do plano `ol-um-outro-agente-graceful-oasis.md`. Define como o app é
> dividido em partes publicáveis separadamente no GitHub Releases, cada uma
> com `sha256` fixado, para que o instalador possa **trazer só a casca** e
> baixar o resto na primeira execução (com verificação de hash e retomada).
>
> **Importante:** o usuário pediu para **subir a versão para o GitHub ser a
> última das prioridades**, então este documento já organiza o trabalho, mas
> a publicação dos assets só acontece quando o programa estiver fechado.

## Convenção de nomes

Os assets são nomeados `Transkript.ai-<versão>-<componente>.zip` (ou `.7z`
se ficar menor) e ficam anexados a cada Release `v4.x.x`. Cada asset tem
um companheiro `Transkript.ai-<versão>-<componente>.sha256` com o hash
SHA-256 do conteúdo, conferido no ato do download.

| Componente | O que é dentro | Quando entra | Tamanho esperado |
|---|---|---|---|
| `casca` | Casca em C# (.NET 10 self-contained) + ícone `app.ico` | sempre | ~115 MB |
| `servidor` | `servidor.exe` empacotado (PyInstaller onedir) + DLLs | sempre | ~80 MB |
| `frontend` | `dist/` da pasta `frontend/` (Vite build) | sempre | ~5 MB |
| `ffmpeg` | ffmpeg/ffprobe do build win64-lgpl-shared (BtbN) | sempre | ~80 MB |
| `cuda` | `ferramentas/cuda/` com cuBLAS/cuDNN | só máquinas com GPU NVIDIA | ~150 MB |
| `modelos-diarizacao` | pyannote/speaker-diarization-community-1 | quando o usuário ativa diarização | ~32 MB |
| `launcher-bootstrap` | casca mínima (publish trim, sem runtime) + script Python que dispara o buscador | sempre que se usa `--bootstrap` | ~5 MB |

> O instalador "completo" (modo `--full`, default do `empacotar.py`) bundle
> todos acima num único `.exe`. O instalador "bootstrap" (modo
> `--bootstrap`) bundle só `casca` + `launcher-bootstrap`, e baixa o resto na
> primeira execução.

## Forma de versionar

Seguindo `MAIOR.MENOR.CORREÇÃO` (igual ao `CHANGELOG.md`). Em Releases
públicos, será `v4.0.0`; alphas de desenvolvimento usam `v4.0.0-alpha.N`.

Cada Release tem o `tag_name`, `name` e um corpo com links para o
`CHANGELOG.md` da versão. Os assets `casca`, `servidor`, `frontend`,
`ffmpeg`, `modelos-diarizacao` e `cuda` são criados por uma execução do
`empacotar.py` com `--separar-assets` antes de subir o Release.

## Onde os assets vão

Diretamente no GitHub Releases da tag. Limite do GitHub: 2 GB por arquivo
(asset), o que sobra para qualquer componente nosso. Banda do
`github.com/jpneto106/Transkript.ai` é generosa para repositório público.

Cada asset é **imutável por tag** — uma vez publicado, o conteúdo não
muda. Se houver bug no asset, faz nova Release (`v4.0.1`).

## Sha256

Sempre publicado como asset companheiro, mesmo nome com `.sha256` no final:

```
Transkript.ai-v4.0.0-casca.zip
Transkript.ai-v4.0.0-casca.zip.sha256
```

Conteúdo do arquivo `.sha256`:
```
<hash em hex>  Transkript.ai-v4.0.0-casca.zip
```

Formato padrão `sha256sum` (com dois espaços e o nome do arquivo).
Compatível com `sha256sum -c` em Linux e com `Get-FileHash -Algorithm SHA256`
no PowerShell.

## Quem baixa o quê

A escolha é feita pelo `instalador/baixar_componentes.py` em três níveis
de decisão, nesta ordem:

1. **O usuário pediu?**
   - Diarização é opt-in (campo `diarizar` em `configuracoes`).
     Se desligado, `modelos-diarizacao` não baixa.
2. **A máquina tem NVIDIA?**
   - Detectada por `detectar_dispositivo()` (já existe em
     `nucleo/dispositivo.py`). Se não, `cuda` não baixa.
3. **Algum asset já está presente e bate o hash?**
   - Se sim, pula — instalação é idempotente. Componentes já em
     `RAIZ_APP/ferramentas/{casca,servidor,frontend,...}` ficam onde estão.

A primeira execução do app dispara o buscador silenciosamente; só mostra
uma janela com a barra de progresso se algo for baixado. Em execuções
subsequentes, ele apenas verifica hashes e segue.

## Como o `--bootstrap` se diferencia do `--full`

```
empacotar.py --full        # default: bundle tudo num .exe de ~700 MB
empacotar.py --bootstrap   # bundle só casca + launcher, outros viram Release assets
```

No modo `--bootstrap`, o launcher é um pequeno script Python
(`launcher-bootstrap/`) que:

1. Verifica se `ferramentas/servidor` está completo. Se não, baixa de
   `Releases/vX.Y.Z/servidor.zip` com sha256 e progress.
2. Mesma coisa para `frontend`, `ffmpeg`, `cuda` (se aplicável) e
   `modelos-diarizacao` (se diarização ligada).
3. Quando tudo está em `RAIZ_APP`, abre a casca normalmente.

A primeira execução demora uns minutos (depende do que falta); depois é
instantâneo.

## O que ainda falta (próximas voltas)

- Ajustar o `instalador/Transkript.ai.iss` (Inno Setup) para emitir os
  dois instaladores (`--full` e `--bootstrap`).
- Integrar o `launcher-bootstrap` na casca, de modo que abrir a casca
  transparente dispare o buscador sem o usuário precisar clicar em mais
  nada.
- Build CI que produza os assets automaticamente quando uma tag é
  publicada (GitHub Actions).
