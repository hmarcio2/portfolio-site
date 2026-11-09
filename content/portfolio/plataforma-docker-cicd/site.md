---
title: O site (gerador estático)
order: 6
summary: "Como este site é feito: conteúdo em Markdown, gerador em Python, templates, paginação, documentação de projetos em várias páginas e testes."
---

Este site é **estático**: HTML puro gerado a partir de Markdown, sem framework de front-end e sem servidor de aplicação (só o chat chama uma API). É o repositório [`portfolio-site`](https://github.com/hmarcio2/portfolio-site).

## Por que um gerador próprio

A necessidade era pequena e específica: uma home, um blog com categorias e paginação, um portfólio com documentação de cada projeto e uma barra de navegação, atualizados **apenas escrevendo Markdown**. Em vez de adotar um gerador pronto, escrevi um de ~380 linhas (`build.py`) com Jinja2, Markdown e PyYAML. O ganho: **zero dependência de front-end**, controle total do HTML e do CSS, e um motivo para escrever testes sobre as regras do site. O custo: manutenção minha, e nenhum dos recursos de um gerador maduro (busca, feeds, imagens otimizadas).

## Como o conteúdo vira páginas

| Entrada | Saída |
|---|---|
| `content/home.md`, `content/curriculo.yml` | `index.html`: quem sou, o resumo do currículo, e os 3 últimos projetos e estudos (preenchidos sozinhos) |
| `content/estudos/*.md` | `estudos/index.html` (cards paginados), uma página por estudo e uma por categoria |
| `content/portfolio/<projeto>/index.md` + `*.md` | `portfolio/index.html` (cards paginados) e, por projeto, uma **visão geral** e uma página por documento, com barra lateral própria |
| `content/portfolio/*.md` (arquivo solto) | Uma página de projeto simples, sem documentação em várias páginas |
| `content/roadmap.md` | `portfolio/roadmap.html`: projetos planejados |
| `content/site.yml` | Nome, links do LinkedIn e do GitHub, categorias, rótulos, tamanho da página |

Cada `.md` começa com um cabeçalho YAML (`title`, `date`, `category`, `summary`, `tags`...), e o corpo é Markdown com tabelas, blocos de código e sumário. Páginas de documentação de projeto usam `title`, `order` e `summary`. Links internos usam `@root/` (por exemplo `[chat](@root/portfolio/chat-do-portfolio/index.html)`), que o gerador troca pelo caminho relativo certo para a profundidade da página.

## O que o gerador faz

- **Ordenação:** do mais recente ao mais antigo; no mesmo dia, o de maior `seq` vem primeiro.
- **Paginação** (6 cards por página, configurável): `index.html`, `pagina-2.html`... e o mesmo por categoria; só aparece quando há mais de uma página.
- **Barra lateral por seção:** categorias em `<details>` (a do texto atual abre sozinha), com o texto atual destacado; categoria sem textos **não aparece**.
- **Projetos com documentação em várias páginas:** a barra lateral passa a mostrar **só as páginas daquele projeto**, em ordem (`order`, depois o nome); cada página tem navegação anterior e próxima e uma lista "Documentação completa" na visão geral.
- **Sumário "Nesta página"** automático em páginas com 3 ou mais títulos `##`.
- **Caminhos relativos:** todas as páginas usam `../` na profundidade certa, então o site **funciona aberto direto do disco** (`file://`), sem servidor.
- **LinkedIn e GitHub no topo de toda página**, e o chat flutuante também.
- **Rascunhos** (`draft: true`) e arquivos começando com `_` são ignorados.
- **Erros de conteúdo** param a geração e dizem o arquivo e o que corrigir (campo faltando, categoria inexistente, data inválida, pasta sem `index.md`, `order` que não é número).
- **Segurança do HTML:** o Jinja escapa o texto dos títulos e resumos (um título com `<script>` não vira script).

## Testes (29)

`tests/test_build.py` e `tests/test_projects.py`, sobre uma cópia do site com conteúdo sintético:

- O **conteúdo real** gera, e **todo link interno resolve** (nenhuma página linka para uma que não existe, e nenhum `@root/` fica sem trocar).
- **LinkedIn e GitHub** aparecem no cabeçalho de **toda** página, e todas têm a navbar e o chat.
- **Links para repositórios** só apontam para repositórios que existem (uma lista fixa), e toda página de projeto tem o botão "Código no GitHub".
- Ordenação (inclusive o desempate por `seq`), paginação com os links anterior e próximo, páginas por categoria, categorias vazias escondidas, sidebar com a categoria aberta, anterior e próximo entre textos, os últimos 3 na home, rascunhos e `_`, escape de HTML nos títulos.
- Projetos em pasta: visão geral e uma página por documento, ordem das páginas e da barra lateral, migalha de pão, anterior e próximo, links com a raiz mais funda, sumário, e os erros claros (sem `index.md`, sem `title`, `order` inválido, arquivo e pasta com o mesmo nome, pasta em `estudos`).

## Do código ao ar

- `python build.py` gera `dist/` (ignorado pelo git). O `dev.ps1` gera e serve em `http://localhost:8080`, junto com a API do chat.
- **O Dockerfile** roda o gerador num estágio Python e copia o HTML para um **nginx sem privilégios** (imagem de 48,5 MB, medida).
- **O CI** roda os testes e o gerador antes do build da imagem.

## Limites

- **Sem busca, sem feed RSS, sem sitemap** e sem imagens otimizadas.
- **Sem tema escuro manual:** o tema segue a preferência do sistema.
- As **datas** dos textos atuais são todas 2026-11-01 (a data em que as medições foram feitas); o `seq` desempata. Edite o campo `date` ao reescrever.
- **O chat precisa de uma API no ar** para responder; sem ela, o widget avisa que não conseguiu falar com o servidor.
- O **gerador é meu**: um bug nele é um bug meu, sem comunidade por trás.
