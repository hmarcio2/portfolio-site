---
title: Ingestão dos dados
order: 2
summary: Como o upload é validado, lido, limpo e carregado, com todos os limites e as decisões de normalização.
---

O arquivo vem de um visitante desconhecido, então a ingestão (`app/data.py`) desconfia de tudo: formato, tamanho, estrutura e conteúdo.

## Validações

| Verificação | Regra | Mensagem ao usuário |
|---|---|---|
| Arquivo vazio | Recusado | "O arquivo está vazio." |
| Formato | Só `.csv` e `.xlsx` (pela extensão) | "Formato não suportado. Envie um arquivo .csv ou .xlsx." |
| Tamanho | Até 5 MB (`PORTFOLIO_SHEETS_MAX_MB`) | "O arquivo excede o limite de 5 MB." |
| `.xlsx` válido | Precisa ser um zip de verdade | "O arquivo não parece um .xlsx válido." |
| *Zip bomb* | O conteúdo descompactado do `.xlsx` não pode passar de 20 vezes o limite de tamanho | "O conteúdo descompactado do arquivo é grande demais." |
| Linhas | Até 200 000 por tabela | "A tabela 'x' tem mais de 200000 linhas." |
| Colunas | Até 100 por tabela | "A tabela 'x' tem mais de 100 colunas." |
| Abas | Até 5 abas com dados | "A planilha tem mais de 5 abas com dados." |
| Sem dados | Tabelas vazias são ignoradas; se não sobrar nenhuma, recusa | "Não encontrei dados na planilha." |

Todos os limites são configuráveis por variável de ambiente ([Operação](@root/portfolio/agente-de-planilhas/operacao.html)). A mensagem de cada recusa é mostrada ao usuário (HTTP 422).

## Leitura

- **CSV:** o separador é detectado automaticamente (`sep=None`), e a codificação é tentada em UTF-8 (com BOM) e, se falhar, em Latin-1, que cobre os CSVs gerados no Excel em português.
- **XLSX:** lido com `openpyxl`, **todas as abas**, depois da checagem de *zip bomb*. Fórmulas chegam como o **último valor calculado** salvo no arquivo (não são recalculadas). `.xls` antigo e arquivos protegidos por senha não são suportados.

## Limpeza e tipos

Para cada aba (uma aba vira uma tabela; o CSV vira uma tabela com o nome do arquivo):

1. **Remove** linhas e colunas completamente vazias.
2. **Normaliza os nomes** de tabelas e colunas: minúsculas, sem acento, só letras, números e `_`, começando com letra, até 60 caracteres, únicos (`Região` vira `regiao`; um nome repetido vira `nome_2`). Isso evita aspas e caracteres estranhos no SQL que o modelo escreve. Um nome vazio ou só com símbolos vira `coluna_N` ou `aba_N`.
3. **Detecta datas** em colunas de texto, mas só quando **todos** os valores são datas no mesmo formato: ISO (`2026-01-05`, com hora opcional) ou brasileiro (`dd/mm/aaaa`); aí a coluna vira `TIMESTAMP`. Uma coluna com um valor que não é data fica como texto (assim não se perdem valores).
4. **Tipos mistos viram texto:** uma coluna com números e palavras misturados vira texto, em vez de falhar ou perder dados.

## Carga no DuckDB

Cada tabela é gravada em **Parquet** num diretório temporário próprio da sessão e carregada (`CREATE TABLE ... AS SELECT * FROM read_parquet(...)`) num DuckDB **em memória**, com `memory_limit` de 512 MB e 2 threads. O Parquet serve como formato intermediário colunar e tipado, o mesmo caminho que usei no projeto real.

Em seguida o banco é **travado** (veja [Segurança do SQL](@root/portfolio/agente-de-planilhas/seguranca-do-sql.html)). O app registra, por tabela, o nome, o número de linhas e as colunas com os tipos, e esse esquema vai para o prompt do modelo e para a interface.

## Sessões

| Parâmetro | Padrão | Variável |
|---|---|---|
| Vida da sessão sem uso | 30 min | `PORTFOLIO_SHEETS_TTL_SECONDS` |
| Análises simultâneas | 30 | `PORTFOLIO_SHEETS_MAX_SESSIONS` |

Passando do máximo de sessões, o upload devolve 503 ("Muitas análises em andamento. Tente novamente em alguns minutos."). Cada leitura de sessão renova o contador de uso; a limpeza de expiradas roda a cada minuto e também a cada upload.

## O que a ingestão não resolve

- **Planilhas "bagunçadas":** cabeçalhos em várias linhas, tabelas lado a lado na mesma aba, células mescladas e totais no meio dos dados são lidos como vierem, e o modelo pode se confundir. A análise assume uma tabela por aba, com cabeçalho na primeira linha.
- **Datas ambíguas** (`03/04/2026`) são lidas como dia/mês/ano, sempre; planilhas em formato americano seriam lidas errado (a coluna só vira data se todas as linhas cabem no formato, mas o dia e o mês podem ser trocados em silêncio).
- **Números como texto** (`"1.234,56"` entre aspas, por exemplo) continuam como texto; o modelo precisa converter no SQL.
- **Dados sensíveis:** não há detecção de dados pessoais na planilha. O conteúdo que o modelo vê vai para o provedor do LLM.
