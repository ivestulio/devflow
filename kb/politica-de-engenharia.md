# Política de Engenharia

## Definição de pronto
Uma tarefa só é considerada pronta quando: existe teste automatizado cobrindo o comportamento
descrito nos critérios de aceite; a mudança passou por revisão de pelo menos uma pessoa; o registro
de mudanças (CHANGELOG) foi atualizado; e a observabilidade (log ou métrica) do caminho alterado
foi verificada.

## Classificação de severidade
`crítica`: perda financeira direta, indisponibilidade total ou vazamento de dados.
`alta`: erro de cálculo visível ao cliente, degradação relevante ou bloqueio de fluxo principal.
`média`: comportamento incorreto com contorno possível.
`baixa`: ajuste cosmético, texto ou melhoria de log.
Prioridade `P0` é reservada para severidade crítica em produção; `P1` para alta; `P2` para média;
`P3` para baixa.

## Estimativa de esforço
A escala é `XS` (até 2 horas), `S` (até 1 dia), `M` (até 3 dias), `L` (até 1 semana) e `XL` (acima
de uma semana, exige quebra em tarefas menores antes de entrar em sprint).

## Mudanças em regras de preço
Qualquer alteração no `pricing-service` que afete valores cobrados exige: teste de regressão com
carrinho real anonimizado, revisão obrigatória de uma pessoa do time de Pagamentos e liberação
gradual por feature flag `pricing.<nome_da_regra>`.
