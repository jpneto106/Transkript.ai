"""Resumo de transcrições por IA (Etapa 7 do plano v4-leve).

Recurso opcional. Por padrão fica DESLIGADO — quando o usuário ativa, ele
escolhe um provedor (LM Studio local, Ollama local, Groq/OpenRouter/OpenAI
remotos, Claude da Anthropic), cola a chave dele, e o programa envia o texto
para o provedor escolhido devolver um resumo em português.

O desenho segue o contrato do Vibe: abstração por cima de qualquer provedor
compatível com a API OpenAI (`/v1/chat/completions`), mais um cliente separado
para a API da Anthropic, que tem outro formato. O usuário não precisa decorar
URLs — os presets embutidos cobrem os provedores mais comuns.

Quem NÃO usa este recurso (a maioria) tem o programa 100% local, como antes.
A frase do README precisa refletir isso: transcrição é local; resumo por IA
na nuvem é opcional e vem desligado.
"""
