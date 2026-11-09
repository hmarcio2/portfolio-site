---
title: Memória e capacidade (VPS de 16 GB)
order: 8
summary: Como os 16 GB estão divididos, o que foi medido e o que é só teto configurado, e quando o plano deixa de caber.
---

A VPS planejada tem **16 GB** de RAM, e todos os projetos devem caber nela. O plano é uma divisão explícita, com **tetos de memória** por container (o Docker mata o container que passar do teto, em vez de deixá-lo tomar a memória dos outros).

## A divisão

| Parte | Teto | Observação |
|---|---|---|
| **Langfuse** (6 serviços) | **8 GiB** exatos | ClickHouse 3,5 + web 1,5 + worker 1 + Postgres 1 + Redis 0,5 + MinIO 0,5; conferido por script no CI e no deploy ([O servidor](@root/portfolio/observabilidade-langfuse/servidor.html)) |
| Chat | 512 MiB | |
| Recomendador de filmes | 768 MiB | |
| Analista de planilhas | 1 GiB | mais um `tmpfs` de 512 MB para os uploads |
| Site (nginx) | 128 MiB | |
| Caddy | sem teto | Pequeno |
| **Apps (tetos)** | **~2,4 GiB** | |
| Sistema operacional e margem | o que sobrar | ~5,6 GiB |

## O que foi medido e o que é só teto

| Container | Medido em repouso (Docker local) | Teto |
|---|---|---|
| Chat | 108 MiB | 512 MiB |
| Filmes | 217 MiB (amostra); **321 MiB** (5000 filmes) | 768 MiB |
| Planilhas | 170 MiB | 1 GiB |
| Langfuse | **não medido** | 8 GiB (configuração) |

Importante:
- As medidas dos apps são **em repouso e depois de poucas requisições**, sem LLM nem embeddings reais. Sob carga, com planilhas grandes ou várias sessões simultâneas, o consumo será maior e **não foi medido**.
- Os tetos do Langfuse são **configuração**, não consumo. Fontes de terceiros indicam 4 GB e 2 vCPU como mínimo e 8 a 16 GB como recomendado para o Langfuse 3 e 4; 8 GiB para os seis serviços é **apertado**.
- **O tmpfs de 512 MB das planilhas conta como memória** do container (os arquivos moram na RAM): somando o DuckDB (até 512 MB por sessão) e o `tmpfs`, o teto de 1 GiB pode ser alcançado com uma planilha grande.

## O que cada componente consome de quê

| Componente | O que pesa |
|---|---|
| Chat | Pouca coisa: o índice BM25 de 54 trechos e as sessões em memória |
| Filmes | O catálogo e o BM25 em memória, o índice Qdrant local, os embeddings; cresce com o número de filmes |
| Planilhas | pandas e DuckDB: **cada sessão** carrega a planilha (até 5 MB de arquivo, 200 mil linhas) num DuckDB próprio de até 512 MB; até 30 sessões |
| Langfuse | O ClickHouse é o que mais cresce com o volume de traces |

## Quando o plano deixa de caber

- **Muitas sessões de planilha simultâneas** com planilhas grandes: o limite de 30 sessões é por contagem, não por memória.
- **Catálogo de filmes maior:** cada filme custa memória no BM25, no Qdrant e no processo; além disso, o índice custa uma chamada de embedding por filme na primeira vez (veja o [risco do índice](@root/portfolio/recomendador-de-filmes/operacao.html)).
- **Langfuse com muito tráfego:** o ClickHouse pede mais que 3,5 GiB.

Saídas, em ordem: subir o teto do ClickHouse (`CLICKHOUSE_MEM`) e reduzir o das planilhas; reduzir o `LANGFUSE_SAMPLE_RATE` dos apps; **migrar o Langfuse para o Cloud** (plano gratuito) e usar o Docker só para desenvolvimento; ou uma VPS maior.

## Como medir de verdade (a fazer)

1. Subir tudo na VPS.
2. `docker stats` com tráfego sintético (por exemplo, dezenas de perguntas e uploads) por cada app e pelo Langfuse.
3. Registrar o pico por container e comparar com os tetos; ajustar e **medir de novo**.
4. Um alerta de memória e de disco na VPS.
