---
title: Limites e próximos passos
order: 8
summary: O que o chat não faz, o que não foi testado e o que vem a seguir.
---

## Limites conhecidos

**De produto**
- **Só sabe o que está na base.** É uma escolha de projeto (evita inventar), mas qualquer fato novo exige atualizar `knowledge/` e reiniciar.
- **Português e inglês.** Outros idiomas caem na busca lexical e podem não achar trechos.
- **Sem memória entre sessões.** O histórico vive 30 minutos e no servidor; reiniciar o container zera as conversas, embora o widget mantenha o texto da aba.

**De engenharia**
- **Estado em memória.** Sessões, taxa por cliente e teto diário não sobrevivem a reinício e não funcionam com várias réplicas (precisariam de Redis).
- **Respostas dependem do LLM.** O Flash-Lite passou nos 16 casos, mas um modelo desse porte pode falhar onde não testei; no [analista de planilhas](@root/portfolio/agente-de-planilhas/ancoragem.html), o mesmo modelo inventou um número que nenhuma consulta produziu.
- **Guardrails só observam.** Nada bloqueia uma resposta ruim antes de ela sair.

**De validação**
- **Uma execução por caso** na avaliação com LLM, sem medir variação.
- **Perguntas escritas por mim**, conhecendo os documentos; o 1,00 de recuperação é otimista.
- **Langfuse:** o envio de traces e notas foi confirmado contra um servidor local, mas sem tráfego real e sem painéis montados.
- **Nunca rodou na VPS** nem no CI do GitHub; só o build e a execução locais em Docker foram feitos.

## Próximos passos

- [ ] Repetir `run_answers` com `--runs 3` para medir variação e comparar com um modelo maior.
- [ ] Casos de ataque mais elaborados (injeção em vários turnos, em outros idiomas).
- [ ] Publicar na VPS e acompanhar as primeiras conversas reais.
- [ ] Criar no Langfuse um painel com as notas (taxa de `injection_suspect`, de `knowledge_gap` e de feedback positivo por semana) e revisar a lista de `knowledge_gap` para ampliar a base.
- [ ] Tirar prints reais da interface do Langfuse (o passo a passo está em `docs/observabilidade/README.md` do repositório).
- [ ] Notas por LLM como juiz (por exemplo, fidelidade da resposta ao contexto): mais caras e não determinísticas; hoje só há as heurísticas.
- [ ] Revisitar a busca híbrida se a base passar de algumas centenas de trechos.

## Decisões que valem ser revistas

| Decisão | Motivo atual | Quando mudar |
|---|---|---|
| BM25 em vez de embeddings | Empatou no acerto@5 e não custa nada | Base com centenas de trechos, perguntas muito parafraseadas ou mais idiomas |
| Estado em memória | Uma réplica basta para uma demo | Mais de uma réplica ou necessidade de manter conversas após reinício |
| Heurísticas como notas, sem LLM juiz | Baratas, determinísticas e auditáveis | Quando o volume permitir pagar por um juiz e comparar com os alertas atuais |
| Gemini Flash-Lite como padrão | O mais barato dos provedores suportados | Se a qualidade das respostas em tráfego real não bastar |
