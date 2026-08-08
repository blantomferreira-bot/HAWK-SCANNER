# HAWK Score

O HAWK Score é um ranking condicional de **0 a 100** para estimar a qualidade relativa de uma oportunidade de expansão de preço. Ele não é uma recomendação financeira e não usa pesos, thresholds, z-scores de corte ou sinais de direção fixos.

## Princípio

Para cada feature `f`, o worker de calibração executa walk-forward validation dentro do regime atual `r` (por exemplo, tendência, volatilidade e liquidez vigentes) e mede o Information Coefficient de Spearman contra o retorno futuro no horizonte escolhido:

```text
IC(f, r) = SpearmanRankCorrelation(feature_f, forward_return)
SE(f, r) = erro-padrão bootstrap do IC(f, r)
C(f, r)  = cobertura observada da feature na amostra de calibração
Q(f, r)  = |IC(f, r)| × C(f, r) / SE(f, r)
```

`Q` é a força estatística dinâmica da feature. Não existe um peso definido no código.

## Normalização dinâmica

Para o ativo `a`, a medição bruta `x(a, f)` é comparada com a distribuição contemporânea do mesmo universo, mesma janela e mesmo regime:

```text
P(a, f, r) = average_rank(x(a, f)) / (N(f, r) + 1)
S(a, f, r) = sign(IC(f, r)) × (2 × P(a, f, r) - 1)
```

`P` é a percentilha empírica; `S` pertence ao intervalo `[-1, 1]`. A direção é aprendida: funding, concentração ou qualquer outra métrica podem mudar de sinal entre regimes se a evidência histórica mudar.

Valores ausentes não recebem zero, média ou qualquer imputação. Eles saem do cálculo e os pesos remanescentes são normalizados novamente.

## Peso de grupos e de features

As features são agrupadas para impedir que uma categoria com muitos campos domine o score. A qualidade de cada grupo também é aprendida via walk-forward:

```text
Q(g, r)       = |IC(g, r)| × C(g, r) / SE(g, r)
W(g, r)       = Q(g, r) / Σj Q(j, r)
w(f | g, r)  = W(g, r) × Q(f, r) / Σk∈g Q(k, r)
```

Logo, cada peso final `w(f | g, r)` depende exclusivamente de força preditiva, incerteza, cobertura, regime e dados disponíveis naquele instante. A soma dos pesos é sempre um.

## Fórmula final

```text
CenteredHawk(a) = Σf w(f | g, r) × S(a, f, r)
HawkScore(a)    = 100 × (CenteredHawk(a) + 1) / 2
Confidence(a)   = Σg W(g, r) × C(g, r)
```

Como `S` está entre `-1` e `1` e a soma de `w` é um, o resultado é matematicamente limitado a `[0, 100]`, sem clamp arbitrário.

## Features e transformações

| Grupo | Feature do algoritmo | Medição base usada antes da percentilha |
|---|---|---|
| Supply | Float | `free_float / total_supply` |
| Valuation | FDV | `fdv / market_cap` |
| Valuation | Market Cap | `market_cap` dentro do universo comparável |
| Derivatives | Open Interest | `open_interest / market_cap` |
| Derivatives | Funding | taxa de funding observada |
| Derivatives | Liquidações | `(short_liquidations - long_liquidations) / (short_liquidations + long_liquidations)` |
| Flows | Exchange Netflow | `exchange_netflow / market_cap` |
| Flows | Whale Activity | `whale_activity / market_cap` |
| On-chain | Holder Growth | `(holders - previous_holders) / previous_holders` |
| DeFi | TVL | `tvl` dentro do universo comparável |
| DeFi | TVL/MC | `tvl / market_cap` |
| Liquidity | Volume Spot | `spot_volume / market_cap` |
| Liquidity | Volume Perp | `perp_volume / open_interest` |
| Liquidity | Spread | spread observado do livro |
| Liquidity | Order Book | `(bid_depth - ask_depth) / (bid_depth + ask_depth)` |
| On-chain | Top Wallets | `top_wallet_balance / free_float` |
| Supply | Token Unlock | `upcoming_unlock / free_float` |
| Attention | Narrativa | índice contínuo de atenção pública fornecido pelo pipeline |
| On-chain | Active Addresses | crescimento percentual de endereços ativos |
| On-chain | Dormancy | dormância observada pelo provedor on-chain |
| On-chain | SOPR | SOPR observado |
| On-chain | MVRV | MVRV observado |
| On-chain | NUPL | NUPL observado |
| On-chain | CVD | variação líquida de CVD no horizonte escolhido |
| Derivatives | Estimated Leverage Ratio | `open_interest / exchange_reserves` |
| Derivatives | Long/Short Ratio | razão long/short observada |

Nenhuma linha da tabela possui uma direção fixa. A orientação final de cada uma é `sign(IC(f, r))`; portanto, por exemplo, um unlock elevado só penaliza ou favorece um ativo quando os dados out-of-sample daquele regime demonstrarem esse efeito.

## Operação do calibrador

O worker deve recalibrar as distribuições de referência, `IC`, `SE`, cobertura e evidência de grupo em cada ciclo de dados. A versão de calibração, regime, horizonte de retorno, universo e timestamp devem ser armazenados junto a cada score para auditoria e backtest.
