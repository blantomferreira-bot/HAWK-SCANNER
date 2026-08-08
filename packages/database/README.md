# Banco de dados — HAWK SCANNER

O modelo Prisma desta pasta é a fonte de verdade do esquema PostgreSQL. Ele cobre identidade, planos e assinaturas, mercado, dados on-chain, pontuação, watchlists, alertas, logs e chaves de API.

## Comandos

Após instalar as dependências do monorepo e configurar `DATABASE_URL`:

- `pnpm --filter @hawk-scanner/database validate` valida o schema.
- `pnpm --filter @hawk-scanner/database generate` gera o Prisma Client.
- `pnpm --filter @hawk-scanner/database migrate:dev` cria e aplica uma migration local.
- `pnpm --filter @hawk-scanner/database migrate:deploy` aplica migrations já versionadas.

## Segurança

`password_hash` e `secret_hash` guardam apenas hashes. O segredo de uma API key nunca é persistido em texto puro. Destinos sensíveis de alertas devem ser criptografados antes da persistência.
