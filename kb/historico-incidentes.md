# Histórico de Incidentes

## INC-2210 — Desconto cumulativo indevido
Em março, um erro no `pricing-service` permitiu que o cupom `FRETEGRATIS` fosse somado ao cupom
percentual, gerando prejuízo de R$ 42 mil em quatro horas. A causa raiz foi a ausência de verificação
de unicidade na lista de cupons quando a cotação era recalculada. A correção introduziu a chave
única `(cart_id, coupon_code)` na tabela `cart_coupons`, mas o caminho de recálculo em memória não
foi coberto.

## INC-2287 — Recálculo ao voltar etapa
Em maio, clientes que voltavam da etapa de pagamento para a de endereço viam o frete zerado. A causa
foi o reaproveitamento de uma cotação em cache sem invalidação na transição de estado. Aprendizado
registrado: toda transição de estado do carrinho deve invalidar a cotação anterior antes de pedir
uma nova.

## Padrão de causa raiz recorrente
Dois dos três incidentes de preço do último ano tiveram origem no caminho de recálculo, não no
caminho de primeira aplicação. Revisões de mudanças em cupom devem inspecionar explicitamente o
recálculo disparado por `cart.state_changed`.
