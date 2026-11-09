---
title: Privacidade dos traces
order: 3
summary: O que é mascarado, o que nunca é enviado, as opções de captura e o que fica por sua conta (retenção e LGPD).
---

Um trace de uma conversa **é um dado pessoal em potencial**: o visitante pode escrever o que quiser, e no analista de planilhas ele envia dados inteiros. A camada de tracing foi desenhada para reduzir isso na origem, antes de qualquer coisa sair do app.

## O que nunca é enviado

- **IP, `user_id` ou qualquer identificação do visitante.** O trace só tem o id **aleatório** da sessão.
- **O nome do arquivo** de uma planilha (pode conter o nome de uma pessoa). Vai só o número de tabelas e de linhas.
- **Chaves e segredos**: o tracer não recebe variáveis de ambiente; só o que o app passa explicitamente.

## O que é mascarado antes do envio

A função `mask_pii` (no `portfolio-core`) troca, em **qualquer** campo (entrada, saída, prompt, metadados, comentários das notas), e em qualquer estrutura (textos, listas e dicionários):

| Padrão | Vira |
|---|---|
| E-mail | `[email]` |
| CPF e CNPJ | `[documento]` |
| Cartão de crédito (13 a 19 dígitos) | `[número]` |
| Telefone brasileiro (com ou sem DDD e `+55`) | `[telefone]` |

Está ligada ao próprio cliente do Langfuse (parâmetro `mask`), então vale também para as observações criadas pelo SDK. Números comuns ("128.158,70 reais", "600 linhas", datas) **não** são mascarados, e há testes para isso.

**Limites do mascaramento:** é feito por padrões. Nomes de pessoas, endereços, números de outros formatos e dados pessoais descritos em texto livre **passam**. Não é anonimização.

## Captura de conteúdo

`LANGFUSE_CAPTURE_CONTENT=false` troca **todo texto** por um marcador com o tamanho (`[conteúdo não registrado: 842 caracteres]`): o trace continua mostrando a estrutura, os tokens, a latência, os erros e as notas, mas não o que foi dito. Os comentários das notas também deixam de ser enviados.

| App | Padrão do exemplo de configuração | Motivo |
|---|---|---|
| Chat | `true` | As perguntas são sobre o meu currículo; o conteúdo é o que permite achar lacunas (`knowledge_gap`) |
| Recomendador de filmes | `true` | Pouco sensível |
| **Analista de planilhas** | **`false`** | Os traces teriam **trechos da planilha do visitante** |

## O que é responsabilidade de quem opera

1. **Aviso ao visitante.** O widget do chat avisa que as conversas podem ser registradas; o analista de planilhas avisa que o conteúdo é processado por uma IA via API.
2. **Retenção.** Defina no projeto do Langfuse por quanto tempo guardar. Os traces crescem, e guardar conversas de visitantes além do necessário é um risco de LGPD.
3. **Acesso.** A interface do Langfuse é pública em `langfuse.SEUDOMINIO` (o cadastro aberto fica desligado); use senha forte, convide só quem precisa e considere restringir por IP no Caddy.
4. **Um projeto por app.** As chaves também *leem* os dados: um vazamento da chave do chat não expõe as planilhas.
5. **Provedor do LLM.** O que o modelo vê vai ao provedor; isso independe do Langfuse. No plano gratuito do Google, em geral, o conteúdo pode ser usado para melhorar produtos: confira os termos antes de aceitar uploads de visitantes.

## Como foi testado

Testes cobrem o mascaramento de e-mail, CPF/CNPJ, telefone e cartão, a preservação de números comuns, o mascaramento em estruturas aninhadas, a captura desligada (nenhum texto sai) e o comentário das notas, que só vai com a captura ligada. A inspeção com o SDK real em memória confirma que o que **seria enviado** já sai mascarado.
