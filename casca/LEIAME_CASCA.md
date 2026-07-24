# Casca nativa (`casca/`)

A janela do Transkript.ai, escrita em C#. Substitui a janela do Microsoft Edge
em modo aplicativo que era usada até a v1.2.0.

## Por que ela existe

| Queixa | Como a casca resolve |
|---|---|
| A barra de tarefas mostrava o logotipo do Edge | A janela é um programa próprio, com o `app.ico` |
| Só funcionava com o Edge instalado | Usa o WebView2, que já vem no Windows 10/11 |
| Cara de navegador, não de programa | Sem barra de endereço, sem abas, sem menu do navegador |

**Nada mudou no `frontend/` nem na `api/`** — só a casca foi trocada.

## Como funciona

```
Transkript.ai.exe   (C# + WebView2)   ← a janela
      │  sobe como processo filho, invisível
servidor Python     (uvicorn + FastAPI)
      │
faster-whisper → GPU ou CPU
```

Ao abrir: escolhe uma porta livre, sobe o servidor, mostra "Iniciando…" até ele
responder em `/api/saude`, e então carrega a interface.

Ao fechar: um **Job Object** do Windows (`KILL_ON_JOB_CLOSE`) mata o servidor
junto. Sem processos órfãos, e a memória da placa de vídeo é liberada.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `Program.cs` | Entrada do programa e descoberta da pasta raiz |
| `JanelaPrincipal.cs` | A janela, o ícone e o WebView2 |
| `Servidor.cs` | Sobe/derruba o servidor Python e o Job Object |

## Compilar e testar

Precisa do **.NET SDK 10** instalado (só na máquina de desenvolvimento — o
programa final não exige nada disso do usuário).

Compilar:

```bash
dotnet build casca -c Debug
```

Testar apontando para a pasta do programa:

```bash
casca\bin\Debug\net10.0-windows\Transkript.ai.exe --raiz C:\Transkript.ai --dev
```

- `--raiz` diz onde ficam `api/`, `venv/`, `dados/` e `app.ico`. Sem ele, a casca
  sobe as pastas a partir do executável procurando `api\main.py`.
- `--dev` libera o menu de contexto e as ferramentas de desenvolvedor do WebView2.
  Sem essa opção, a janela fica com cara de programa fechado.

## Gerar a versão final (autossuficiente)

Não exige runtime na máquina do usuário:

```bash
dotnet publish casca -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false
```

> `PublishSingleFile=false` é proposital: arquivo único descompacta em pasta
> temporária a cada abertura e pode deixar resíduo. Ver a regra 7 do plano da v2.

## Onde o servidor final vai entrar

Quando a Etapa 2 do plano (empacotar com PyInstaller) estiver pronta, a casca
passa a procurar `servidor\servidor.exe` na raiz e usa ele em vez do `venv`.
Essa lógica **já está escrita** em `Servidor.MontarComando()` — o `venv` é
apenas o caminho alternativo, para desenvolvimento.
