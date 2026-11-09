---
title: Arquitetura
order: 1
summary: Componentes, o caminho de um upload e de uma pergunta, e o ciclo de vida dos dados do usuário.
---

## Componentes

| Componente | Arquivo | Papel |
|---|---|---|
| Ingestão | `app/data.py` | Valida o arquivo, lê CSV/XLSX, limpa nomes e tipos, converte para Parquet e carrega num DuckDB **travado** por sessão; guarda as sessões e apaga os arquivos |
| SQL seguro | `app/sql_guard.py` | Valida a consulta (uma instrução, só SELECT), executa com timeout e limite de linhas, converte os valores para JSON |
| Ferramentas | `app/tools.py` | `describe_table`, `run_sql` e `make_chart`, com validação dos argumentos |
| Agente | `app/agent.py` | Prompt de sistema, ligação das ferramentas ao loop de agente do `portfolio-core` e a checagem de ancoragem |
| Ancoragem | `app/grounding.py` | Confere os números grandes da resposta contra os resultados das consultas |
| Notas | `app/guardrails.py` | As notas que vão para o trace do Langfuse |
| Relatório | `app/report.py` | Gera o Markdown da análise |
| API | `app/main.py` | FastAPI: upload, chat (SSE), relatório, exclusão, health e a interface |
| Interface | `web/` | Upload por arrastar e soltar, esquema das tabelas, chat, gráficos (Chart.js) e download do relatório |

## O caminho de um upload

1. **Limite de taxa:** 5 uploads por minuto por cliente.
2. **Leitura e validação** (detalhes em [Ingestão dos dados](@root/portfolio/agente-de-planilhas/ingestao.html)): só `.csv` e `.xlsx`, tamanho, número de linhas, colunas e abas; nomes normalizados; datas e tipos tratados.
3. **Parquet:** cada tabela é gravada num arquivo Parquet num diretório temporário próprio da sessão.
4. **DuckDB:** um banco **em memória, por sessão**, carrega os Parquets (memória limitada a 512 MB, 2 threads). **Depois da carga, o banco é travado**: sem acesso a arquivos nem rede, sem extensões, configuração bloqueada.
5. **Resposta:** o `session_id` (token aleatório de 16 bytes), o nome do arquivo e o esquema das tabelas (nome, linhas, colunas e tipos).

## O caminho de uma pergunta

1. A sessão é buscada (404 se não existe ou expirou) e a mensagem, validada (1 a 1000 caracteres). Taxa por minuto e teto diário (429).
2. Abre-se o trace `sheet-turn`.
3. O **esquema das tabelas** vai no prompt de sistema. O modelo pede `describe_table` quando não conhece uma coluna e `run_sql` para calcular; erros de SQL voltam como observação para ele se corrigir; `make_chart` desenha o resultado da última consulta. O teto é de 8 passos.
4. A cada passo saem eventos SSE: `tool` (o que foi chamado), `chart`, `delta` (texto).
5. **Checagem de ancoragem:** ao final, os números grandes da resposta são comparados com o que as consultas devolveram; os que não aparecem geram o evento `warning` ([Ancoragem](@root/portfolio/agente-de-planilhas/ancoragem.html)).
6. A resposta, o SQL e os gráficos entram no relatório da sessão; o trace recebe a resposta e as notas.

## Ciclo de vida dos dados do usuário

A planilha é dado do visitante, então o ciclo é curto e explícito:

- **Em memória e em diretório temporário**, nunca num banco compartilhado. Cada sessão tem o seu DuckDB e o seu diretório.
- **Apagada** (arquivos e conexão) após **30 minutos sem uso**, ao clicar em "Nova planilha" (`DELETE /sessions/{id}`) ou ao desligar o app. Uma tarefa de limpeza roda a cada minuto.
- **Sem login:** o `session_id` aleatório funciona como credencial da análise. Quem o tem acessa a sessão, então ele não deve ser compartilhado.
- **No Docker,** `/tmp` é `tmpfs` (512 MB): nada persiste em disco e tudo some ao reiniciar.
- **O conteúdo da planilha vai ao provedor do LLM** (as linhas que o modelo vê em cada consulta). A interface avisa para não enviar dados sensíveis.

## Decisões de arquitetura

- **DuckDB em memória por sessão**, e não um banco compartilhado: isolamento simples, descarte barato e nenhuma chance de uma sessão ler a de outra.
- **Loop de agente no `portfolio-core`**: o mesmo do recomendador de filmes; cada app só define prompt, ferramentas e a função que as executa. Antes ele era um loop manual deste projeto, para emitir eventos de progresso (SQL, gráfico) durante o streaming e controlar o teto de passos.
- **Histórico entre perguntas guarda só o texto** das respostas, não os resultados das ferramentas: perguntas de acompanhamento que dependem de números anteriores fazem o agente consultar de novo. Mais barato, ao custo de uma consulta a mais.
- **Fórmulas do Excel** chegam como o último valor calculado salvo no arquivo; não são recalculadas.
