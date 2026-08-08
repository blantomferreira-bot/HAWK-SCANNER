# Operação do scanner automático

O scheduler chama o worker via REST a cada dez minutos. O worker rejeita chamadas sem `X-Scheduler-Token` válido e protege a execução com um lock Redis de uma janela de scan.

```text
Scheduler -- POST /internal/scanner/run --> Worker
Worker --> CoinGecko / Binance públicos
Worker --> PostgreSQL (metrics, history, scores, score_history, scanner alerts)
Worker --> Telegram / Discord / SMTP
Scheduler -- POST /internal/ml/train --> Worker (diariamente)
```

## Persistência e deduplicação

- Cada rodada cria um registro em `scanner_runs`.
- Métricas e candles são append-only, preservando o histórico.
- O ranking é atualizado pelos registros mais recentes de `scores`.
- `scanner_alerts` tem unicidade por moeda e snapshot de score; uma mesma avaliação não é enviada duas vezes.
- Cada tentativa de entrega fica registrada em `scanner_alert_deliveries`, com destino, horário, status e erro.

## Configuração necessária

Configure `INTERNAL_SCHEDULER_TOKEN` de forma idêntica no worker e scheduler. Configure os destinos Telegram, Discord e SMTP no worker. Ausência de um canal não interrompe a coleta, cálculo ou os outros canais.
