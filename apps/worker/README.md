# HAWK SCANNER worker

O worker expõe `POST /internal/scanner/run` para o scheduler interno e executa um ciclo idempotente protegido por lock Redis.

Em cada ciclo ele:

1. Lê todas as moedas e mercados ativos do PostgreSQL.
2. Atualiza preço, market cap e volume pelo CoinGecko; e preço, volume, spread e book ticker pela Binance quando configurada.
3. Persiste métricas e candles de dez minutos em `metrics` e `history`.
4. Calcula retornos realizados desde o ciclo anterior, recalibra o Hawk Score e grava `scores` e `score_history`.
5. Atualiza o ranking, que é a ordenação dos snapshots mais recentes de `scores`.
6. Para cada score estritamente maior que `HAWK_ALERT_THRESHOLD` (85 por padrão), grava `scanner_alerts` e entregas em `scanner_alert_deliveries`.
7. Entrega o alerta pelos canais configurados: Telegram, Discord e e-mail SMTP.

As primeiras execuções fazem warm-up: o Hawk Score não inventa pesos sem evidência de retorno observada. Após existir histórico, o calibrador passa a emitir scores dinâmicos.

O mesmo worker executa `POST /internal/ml/train` diariamente para treinar o modelo XGBoost de Similarity Score. Consulte `docs/scoring/ml-similarity.md` para o protocolo de treino e dados necessários.
