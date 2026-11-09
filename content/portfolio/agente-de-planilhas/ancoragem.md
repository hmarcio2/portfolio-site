---
title: Ancoragem dos números
order: 5
summary: Como o app confere se os números grandes da resposta vieram de uma consulta, o algoritmo, o que ele pega, e o que não pega.
---

## O problema

Um modelo pequeno às vezes **completa a resposta com um número plausível, sem ter consultado nada**. Medido com o Gemini Flash-Lite: numa pergunta sem resposta possível ("qual foi o lucro?", numa planilha sem coluna de custo), o modelo negou corretamente, mas **ofereceu uma "receita total de R$ 96.069,57" sem rodar SQL**. O valor real da receita era R$ 128.158,70. Veja o relato completo no estudo [O agente de SQL inventou um número](@root/estudos/agente-sql-ancoragem-de-numeros.html).

Pedir "não invente números" no prompt reduz a chance, mas não dá garantia. A defesa tem de ser **mecânica**: conferir a resposta depois de escrita.

## A ideia

Não dá para provar que um número está *certo*, mas dá para apontar os que **não vieram de nenhuma consulta**. Ao fim de cada resposta, `app/grounding.py`:

1. **Junta a evidência:** todos os números que apareceram nos resultados das ferramentas daquela resposta (lidos do JSON, sem adivinhar formato), mais os números que o usuário citou na pergunta e na conversa anterior (esses não contam como inventados).
2. **Extrai os números da resposta** e os interpreta em notação brasileira (`1.234,56`) ou americana (`1,234.56`), distinguindo o separador decimal do de milhar pelo último separador e pelo tamanho do trecho depois dele.
3. **Compara:** cada número ≥ 1000 que **não bate** com a evidência é sinalizado.

### Regras que evitam alarme falso

| Regra | Por quê |
|---|---|
| Só números **≥ 1000** são checados | Percentuais e contagens pequenas costumam ser derivados pelo próprio modelo (uma média, "3 de 5"), e verificá-los geraria falsos alarmes |
| **Anos** (inteiros entre 1900 e 2100) são ignorados | "Em 2026" não é um dado inventado |
| Tolerância de **0,5%** (mínimo de 0,01) | Aceita arredondamentos e "128 mil" para 128 158,70 |
| Números da pergunta e da conversa anterior contam como conhecidos | O usuário pode citar um valor e o modelo repeti-lo |
| Os números dos resultados são lidos como números, inclusive os que aparecem dentro de textos (datas, "1.234") | Cobre os valores que o SQL devolve como texto |

## O que o usuário vê

Os números sinalizados geram o evento SSE `warning` (`{"unverified": ["96.069,57"]}`), enviado **antes** do `done`. A interface mostra: "Atenção: ... não aparece(m) nos resultados das consultas desta resposta. Confira-os antes de usar." O relatório `.md` traz o mesmo aviso na resposta correspondente. O nível de confiança fica com o usuário: o app só aponta.

O mesmo resultado vira uma **nota** `unverified_numbers` no trace do Langfuse, para medir a frequência ([Observabilidade](@root/portfolio/agente-de-planilhas/observabilidade.html)).

## O que ele pega

- Um valor inventado, sem relação com os dados: o caso do R$ 96.069,57.
- Uma resposta que **não rodou consulta nenhuma** e mesmo assim cita números grandes.
- Uma troca de métrica (a receita apresentada como lucro) **não** é pega por si só, porque o número veio de uma consulta; essa falha é tratada pela regra do prompt e por um caso da avaliação.

## O que ele NÃO pega (limites honestos)

- **Não prova que o número está certo**, só que veio de uma consulta. Uma consulta errada gera um número "ancorado" e errado.
- **Números pequenos e percentuais** derivados pelo modelo não são checados (de propósito, para evitar falsos alarmes).
- **Coincidência:** um valor inventado que, por acaso, bata com outro número dos resultados passa (a tolerância de 0,5% aumenta a chance).
- **Números por extenso** ("cento e vinte mil") não são lidos.
- **Formato:** números em formatos que o interpretador não conhece (como `1 234,56` com espaço) podem ser lidos errado.

## Como foi testado

`tests/test_grounding.py` cobre a leitura de números em vários formatos (brasileiro e americano), a leitura dos números dos resultados a partir do JSON (sem adivinhar formato), o aceite do mesmo número em qualquer notação, o alerta para um número grande inventado, o silêncio para números pequenos, anos e números da pergunta, cada número sinalizado uma vez só, e a integração: com um provedor roteirizado, o agente avisa sobre um número que nenhuma consulta produziu, fica em silêncio quando os números vêm da consulta, e o aviso chega ao cliente e ao relatório. Na avaliação com o LLM real, o caso `inexistente` agora **reprova** quando aparece um número não verificado, e passou 9 de 9 na rodada final ([Avaliação](@root/portfolio/agente-de-planilhas/avaliacao.html)).

## O que isso diz sobre avaliação

O número inventado **só apareceu na revisão manual** das respostas: a checagem por palavra-chave da avaliação tinha aprovado aquela execução. Duas lições: ler as respostas, não só o placar; e transformar a falha em **verificação em tempo de execução**, que protege o usuário, e em **caso de avaliação**, que protege contra regressão.
