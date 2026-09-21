# Padrões de Teste

## Pirâmide adotada
Cobertura obrigatória de teste unitário para toda regra de negócio em `pricing-service`. Testes de
integração ficam em `tests/integration` e usam banco efêmero via contêiner. Testes ponta a ponta do
checkout rodam apenas no pipeline noturno, por serem lentos.

## Testes de regressão de preço
Bugs de cálculo exigem um caso de teste que reproduza o cenário exato do defeito antes da correção
(teste que falha primeiro). O arquivo padrão é `tests/unit/pricing/test_coupon_regression.py`, com
o identificador da issue no nome do teste, por exemplo `test_issue_1042_cupom_duplicado`.

## Cenários mínimos para cupom
Todo ajuste em cupom precisa cobrir: cupom válido aplicado uma vez; tentativa de aplicar o mesmo
cupom duas vezes; dois cupons diferentes cumulativos; cupom expirado; e recálculo após navegação
de volta na máquina de estados do carrinho.
