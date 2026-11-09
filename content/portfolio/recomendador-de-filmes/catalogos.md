---
title: Catálogos de filmes
order: 2
summary: As três fontes de dados (amostra, CMU e TMDB), como o catálogo grande é preparado, o idioma e as licenças.
---

O catálogo é um CSV com `id`, `title`, `year`, `genres` (separados por `|`), `rating`, `votes`, `overview` (a sinopse) e `poster_path`. Filmes sem título ou sem sinopse são descartados: sem sinopse não há o que comparar. A fonte é escolhida por `PORTFOLIO_FILMES_CATALOG` (`sample`, `cmu` ou `tmdb`); sem isso vale o primeiro arquivo que existir, nesta ordem: TMDB, CMU, amostra.

## As três fontes

| Fonte | Filmes | Idioma | Notas e pôsteres | Licença / termos | Estado |
|---|---|---|---|---|---|
| **Amostra** (`data/sample_movies.csv`) | 44 | português | não | sinopses escritas por mim | embutida, roda offline |
| **CMU Movie Summary Corpus** (`scripts/prepare_cmu.py`) | 5000 (de 42 mil) | inglês | não | CC BY-SA, com a atribuição exibida no app | testada, com índice e avaliação |
| **TMDB** (`scripts/fetch_tmdb.py`) | cerca de 1000 | português (pt-BR) | sim | uso não comercial, com atribuição | script **nunca testado** contra a API real |

### Por que não o IMDb

Os datasets oficiais do IMDb têm título, ano, gêneros e nota, mas **não têm sinopse**, e a busca precisa de um texto para comparar. Dá para usar o IMDb para notas, mas não para esta busca.

## O catálogo CMU

O CMU Movie Summary Corpus (Bamman, O'Connor e Smith, ACL 2013) reúne as sinopses de 42 mil filmes extraídas da Wikipedia em inglês (dump de 2012), mais metadados do Freebase: título, data, bilheteria e gêneros. É o que o `prepare_cmu.py` transforma em `data/cmu_movies.csv` (ignorado pelo git, 7 MB).

```powershell
# baixe https://www.cs.cmu.edu/~ark/personas/data/MovieSummaries.tar.gz (cerca de 46 MB) e extraia
..\.venv\Scripts\python scripts\prepare_cmu.py --src C:\caminho\MovieSummaries --max 5000
```

O que o script faz:

1. **Limpa a marcação da Wikipedia** que sobrou nas sinopses: modelos (`{{plot}}`, `{{cite web}}`), notas (`<ref>`), links (`[[...]]`) e entidades HTML (`&nbsp;`). Frases em que sobrou marcação quebrada (por exemplo, uma citação cortada no meio) são descartadas inteiras. Verifiquei que nenhuma sinopse final tem `{{`, `[[`, `<`, `|` nem `http`.
2. **Descarta sinopses com menos de 300 caracteres** e **corta as maiores em 1500**, na última frase inteira que cabe.
3. **Converte os metadados:** o ano vem do início da data (e é ignorado se inválido), os gêneros do Freebase viram uma lista (no máximo 6) e três gêneros sem significado ("World cinema", "Indie", "Black-and-white") são removidos.
4. **Escolhe os filmes:** o índice precisa de um embedding por filme, e com 42 mil filmes isso levaria horas no Ollama ou estouraria a cota gratuita do Google. Quando há mais filmes que vagas (`--max`, padrão 5000), ficam **primeiro os que têm bilheteria registrada, do maior para o menor**, e depois os de sinopse mais longa.

**Cuidado com essa escolha:** bilheteria é um indício de popularidade, **não de qualidade nem de tema**. O catálogo resultante é bom para filmes conhecidos e fraco em nichos (por exemplo, animações antigas sobre brinquedos, ou filmes de países com pouca bilheteria registrada).

**O que os dados têm de estranho:** o corpus vem de uma extração automática do Freebase, então há gêneros demais (279 no recorte de 5000), com nomes como "Action Thrillers" ao lado de "Action". Por isso o prompt lista só os 40 gêneros mais comuns, e as ferramentas aceitam filtro por gênero com casamento por prefixo.

## O idioma do catálogo

Cada fonte tem um idioma (`pt` para a amostra e o TMDB do script, `en` para o CMU), que pode ser sobrescrito por `PORTFOLIO_FILMES_CATALOG_LANG`. O idioma entra no prompt: com um catálogo em inglês, o agente é instruído a **escrever a consulta em inglês, traduzindo o pedido do usuário**, e a usar o título original em inglês quando citar um filme de exemplo. Detalhes em [Agente e ferramentas](@root/portfolio/recomendador-de-filmes/agente.html).

## Atribuição e licença

- **CMU:** a licença é CC BY-SA, que exige citar a fonte. O app mostra, no rodapé, "Sinopses e metadados: CMU Movie Summary Corpus (Bamman, O'Connor e Smith, ACL 2013), licença CC BY-SA; as sinopses vêm da Wikipedia em inglês.". Como é *share-alike*, redistribuir o catálogo derivado exigiria a mesma licença; por isso o CSV não vai para o repositório (cada pessoa gera o seu).
- **TMDB:** os termos exigem atribuição ("Este produto usa a API do TMDB, mas não é endossado nem certificado pelo TMDB") e **restringem o uso comercial**; confira-os antes de publicar.

## Atualizar ou trocar o catálogo

1. Gere o novo CSV com o script correspondente (em `data/`, ou na pasta de `PORTFOLIO_FILMES_CATALOG_DIR`).
2. Reinicie o app. O índice é recriado sozinho se o catálogo ou o embedder mudou (o nome da coleção muda), o que **chama o embedder para cada filme**: veja o custo em [Operação](@root/portfolio/recomendador-de-filmes/operacao.html).
