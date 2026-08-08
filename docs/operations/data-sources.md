# Fontes obrigatórias de dados

Cada execução do scanner consulta e grava o status de todas as fontes abaixo em `logs`. Com `REQUIRE_ALL_DATA_SOURCES=true` (padrão), qualquer falha ou credencial ausente marca a rodada como falha antes de atualizar scores ou ranking.

| Fonte | Uso no HAWK SCANNER | Credencial |
|---|---|---|
| CoinGecko | preço, market cap, FDV, volume e metadados | opcional para ping; recomendada para dados de mercado |
| CoinGlass | funding, OI, liquidações e long/short | `COINGLASS_API_KEY` |
| DeFiLlama | TVL, TVL/MC, unlocks e métricas de protocolo | `DEFILLAMA_API_KEY` |
| Binance | ticker, volume, spread, profundidade e derivativos | pública |
| Coinbase | mercado spot e livro público | pública |
| HyperLiquid | funding, mark price e open interest perp | pública |
| Bitquery | DEX, transfers, holders, wallets e atividade multichain | `BITQUERY_API_KEY` |
| Covalent | balances, atividade e dados multichain indexados | `COVALENT_API_KEY` |
| Alchemy | RPC, token balances e transfers EVM | `ALCHEMY_API_KEY` |
| Moralis | holders, transfers, swaps, liquidez e narrativa on-chain | `MORALIS_API_KEY` |
| Etherscan | Ethereum: holders, supply e ERC-20 transfers | `ETHERSCAN_API_KEY` |
| BscScan | BNB Chain: holders, supply e BEP-20 transfers | `BSCSCAN_API_KEY` |
| Arbiscan | Arbitrum: holders, supply e ERC-20 transfers | `ARBISCAN_API_KEY` |
| BaseScan | Base: holders, supply e ERC-20 transfers | `BASESCAN_API_KEY` |
| Solscan | Solana: holders, transfers e atividade de token | `SOLSCAN_API_KEY` |

O worker não usa scraping. Cada adaptador chama a API oficial por HTTPS, respeita o contrato de autenticação do provedor e registra disponibilidade/falhas em vez de substituir dados faltantes por valores sintéticos.
