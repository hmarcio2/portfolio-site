---
title: Limites e próximos passos
order: 10
summary: O que o analista não faz, o que não foi medido e o que vem a seguir.
---

## Limites conhecidos

**Dos dados**
- **Formatos:** só `.csv` e `.xlsx`; `.xls` antigo e arquivos com senha não são suportados.
- **Fórmulas do Excel** chegam como o último valor calculado salvo; não são recalculadas.
- **Planilhas bagunçadas** (cabeçalhos em várias linhas, tabelas lado a lado, células mescladas, totais no meio) são lidas como vierem, e o modelo pode se confundir.
- **Tamanho:** até 5 MB, 200 mil linhas, 100 colunas e 5 abas por padrão.

**Do agente**
- **O modelo pode errar a interpretação** mesmo com o número certo: a checagem de ancoragem prova que o número **veio de uma consulta**, não que a consulta responde à pergunta.
- **Números pequenos e percentuais** derivados pelo modelo não são conferidos.
- **O histórico guarda só o texto:** perguntas de acompanhamento que dependem de resultados anteriores refazem a consulta.
- **Um modelo pequeno:** o Flash-Lite errou o caso do "lucro" na primeira rodada e inventou um número; foi corrigido e medido, mas outros casos que não testei podem falhar.

**De privacidade e operação**
- **O conteúdo que o modelo vê vai ao provedor do LLM** (30 linhas por consulta, células de até 200 caracteres). A interface avisa; não há detecção de dados pessoais.
- **Sem login:** o `session_id` aleatório é a credencial da análise.
- **Estado em memória:** reiniciar o container apaga as sessões (e os arquivos, que estão em `tmpfs`).

**De validação**
- **A rodada completa de avaliação não foi repetida** depois das correções; só 3 das 10 perguntas foram re-medidas.
- **Planilha sintética**, perguntas de resposta única; **perguntas abertas e planilhas ambíguas não foram avaliadas**.
- **Nunca rodou na VPS** nem no CI do GitHub.

## Próximos passos

- [ ] Repetir a rodada completa (10 perguntas × 3 execuções) com o código atual e comparar com o Ollama local e com um modelo maior (modelo × acertos × custo).
- [ ] Avaliar perguntas abertas (insights) e planilhas com colunas ambíguas.
- [ ] Conferir os termos do plano gratuito da API do Google antes de expor a demo (veja [Operação](@root/portfolio/agente-de-planilhas/operacao.html)).
- [ ] Validar os traces com tráfego real, calcular o **custo por conversa** e decidir a retenção.
- [ ] Exportar o relatório também em PDF ou DOCX, com os gráficos.
- [ ] **Cache de prompt** do esquema e das ferramentas (um prefixo estável por sessão), para baixar o custo por pergunta.
- [ ] Detectar o formato de data americano e dados pessoais na planilha antes de enviar ao provedor.

## Decisões que valem ser revistas

| Decisão | Motivo atual | Quando mudar |
|---|---|---|
| DuckDB em memória por sessão | Isolamento e descarte baratos | Planilhas grandes ou análises que precisem sobreviver a reinício |
| Só 30 linhas visíveis ao modelo | Custo e privacidade | Se o modelo precisar de amostras maiores para entender colunas difíceis |
| Checagem de ancoragem só para números ≥ 1000 | Evita falsos alarmes com percentuais | Se a taxa de números pequenos inventados for relevante |
| Captura de conteúdo desligada nos traces | Os dados são do visitante | Se for preciso depurar com conteúdo, com retenção e aviso definidos |
| Gemini Flash-Lite como padrão | O mais barato; passou nas perguntas medidas | Se o custo de erros (cota, SQL errado) superar a economia |
