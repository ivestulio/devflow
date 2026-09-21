# Runbook de Pagamentos

## Contatos e janelas
O time de Pagamentos é responsável por `pricing-service` e `payment-gateway`. A janela de deploy é
de segunda a quinta, das 10h às 16h. Correções de severidade crítica podem ir fora da janela com
aprovação do plantão.

## Feature flags de preço
Toda regra de desconto roda atrás de uma flag no formato `pricing.<nome_da_regra>`. A flag começa em
0% do tráfego, sobe para 10%, 50% e 100% com pelo menos 30 minutos de observação em cada degrau.
O painel de acompanhamento é `Grafana > Pricing > Cupons`.

## Métricas de cupom
As métricas relevantes são `pricing_coupon_applied_total`, `pricing_coupon_rejected_total` e
`pricing_quote_total_amount`. Uma queda anômala em `pricing_quote_total_amount` sem queda
correspondente no volume de pedidos indica desconto aplicado indevidamente.
