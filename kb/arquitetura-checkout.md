# Arquitetura do Checkout

## Visão geral dos serviços
O fluxo de compra da Loja Aurora é dividido em quatro serviços: `checkout-web` (frontend em React),
`checkout-api` (BFF em Node.js), `pricing-service` (cálculo de preços, descontos e cupons, em Python)
e `payment-gateway` (integração com adquirentes). O `checkout-web` nunca calcula valores: ele apenas
exibe o total devolvido pelo `pricing-service` através do `checkout-api`.

## Máquina de estados do carrinho
O carrinho tem os estados `RASCUNHO`, `ENDERECO`, `PAGAMENTO` e `CONFIRMADO`. A navegação para trás
é permitida entre `ENDERECO` e `PAGAMENTO`. Cada transição emite o evento `cart.state_changed` e
dispara uma nova chamada de `POST /pricing/quote`. Voltar de etapa NÃO limpa o carrinho, apenas
recalcula a cotação.

## Aplicação de cupons
Cupons são aplicados exclusivamente no `pricing-service`, no módulo `pricing/discounts/coupon.py`.
A função `aplicar_cupom` recebe o carrinho e a lista de cupons já aplicados. A regra de negócio diz
que um mesmo código de cupom só pode incidir uma vez por cotação. A lista de cupons aplicados é
persistida na tabela `cart_coupons`, com chave única `(cart_id, coupon_code)`.

## Idempotência de cotação
Toda chamada a `POST /pricing/quote` deve ser idempotente para o mesmo `cart_id` e mesma composição
de itens. O cabeçalho `Idempotency-Key` é obrigatório desde a versão 3.4 do `checkout-api`. Chamadas
sem a chave são aceitas por retrocompatibilidade, mas registram um `WARN` em `pricing.quote.legacy`.
