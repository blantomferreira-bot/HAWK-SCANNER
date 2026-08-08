# Módulo diário de IA: Breakout Similarity

## Objetivo e modelos

Todos os dias, o worker treina dois modelos independentes para cada moeda ativa:

| Modelo | Janela de contexto | Evento positivo |
|---|---:|---:|
| Breakout amplo | 90 dias | retorno futuro acima de 300% |
| Explosive Move Discovery | 30 dias | retorno futuro acima de 500% |

Para um alvo com horizonte `H` e limiar `T`, uma fotografia vira evento positivo quando:

```text
RH(a, t) = Price(a, t + H) / Price(a, t) - 1
label(a, t) = 1, se RH(a, t) > T; caso contrário, 0
```

Os limiares e janelas acima são definições explícitas do produto. Não existem regras manuais que digam que funding, whales, unlock ou qualquer outra feature devem ser positivos ou negativos.

## Dados da janela de 90 dias

Para cada moeda o feature store registra, quando disponíveis, funding médio e dispersão, comportamento de open interest, valor e frequência de transferências de whales, atividade on-chain, volume e volatilidade de volume, contagem de wallets e whale wallets, narrativa, pressão de unlock e float ratio. Para cada tipo de métrica também produz média, desvio, mínimo, máximo, primeira e última observação, amplitude relativa e contagem da janela. Isso gera aproximadamente 100 features quando a cobertura de dados do ativo permite.

Os valores vêm de `funding`, `open_interest`, `transfers`, `wallets`, `whales`, `metrics`, `history` e das métricas customizadas de fornecedores públicos. Dados ausentes continuam ausentes: o XGBoost lida com valores faltantes nativamente; não há preenchimento com zero, média ou valor arbitrário.

## Treinamento diário

1. O scheduler chama `POST /internal/ml/train` uma vez por dia.
2. O worker grava `ml_feature_snapshots` de todas as moedas ativas, com preço de referência, início e duração da janela.
3. Fotografias com preço disponível após o horizonte de cada modelo tornam-se exemplos rotulados; todas as moedas participam, inclusive as que não tiveram breakout.
4. O dataset é ordenado por tempo e avaliado em walk-forward validation. Um fold nunca treina com observações futuras do seu período de validação.
5. Um XGBoost binário é treinado para estimar `P(RH > T)` de cada modelo.
6. O desequilíbrio de classes é recalculado a cada dia por `n_negativos / n_positivos`. A complexidade do modelo e o número de árvores são derivados do tamanho corrente do dataset e do número de features, e ficam armazenados em `ml_training_runs`.
7. O artefato XGBoost, features, métricas AUC-ROC/Average Precision walk-forward e hiperparâmetros são versionados no mesmo registro.

Assim, pesos, interações, relações não lineares, valores faltantes e a importância de cada variável são aprendidos pelo modelo do dia. Nenhuma feature recebe peso pré-definido.

## Similarity Score

O XGBoost envia cada observação para uma sequência de folhas. Seja `L(a)` o vetor de folhas da moeda atual e `L(e)` o vetor de folhas de um evento histórico positivo. A similaridade de folha é:

```text
LeafAgreement(a, e) = mean_j[ L_j(a) = L_j(e) ]
Similarity(a) = 100 × mean_e∈EventosPositivos[LeafAgreement(a, e)]
```

O score é de 0 a 100 e compara cada moeda atual contra todos os padrões históricos de moedas que superaram 300%. Como as folhas derivam de splits e interações aprendidos pelo XGBoost, não há distância euclidiana manual, seleção fixa de variáveis ou pesos definidos por regra.

`MlSimilarityScore` persiste três informações: Similarity Score, probabilidade do classificador e leaf agreement. Elas permitem distinguir uma moeda estruturalmente parecida com breakouts passados de uma previsão probabilística pontual.

## Warm-up e integridade

Antes de haver ao menos um conjunto temporal com exemplos positivos e negativos após os 90 dias, o treinamento fica em `WARMING_UP`. O sistema não cria um modelo artificial nem um Similarity Score com dados insuficientes. Cada execução e eventual erro ficam em `ml_training_runs`.
