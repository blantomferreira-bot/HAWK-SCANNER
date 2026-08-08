# HAWK SCANNER API

API REST versionada em FastAPI. Todos os endpoints de produto estão sob `/api/v1`; a interface OpenAPI está disponível em `/docs` e a especificação JSON em `/openapi.json`.

## Endpoints

- Dados públicos: `/coins`, `/coin/{id}`, `/ranking`, `/metrics`, `/funding`, `/openinterest`, `/liquidations`, `/holders` e `/score`.
- Autenticação JWT: `/auth/register`, `/auth/login`, `/auth/refresh` e `/auth/me`.
- Usuário autenticado: `/watchlist` e `/alerts`.
- Administração com RBAC: `/admin`, `/admin/users` e `/admin/plans`.

O arquivo Prisma em `packages/database/prisma/schema.prisma` é a fonte de verdade para migrations. Esta API usa SQLAlchemy assíncrono apenas como adaptador de leitura/escrita do mesmo PostgreSQL, impedindo que a camada HTTP tenha dependência direta de detalhes do banco.

## Execução local

1. Copie `.env.example` para `.env` e forneça um segredo JWT seguro.
2. Instale as dependências do `pyproject.toml` com seu gerenciador Python.
3. Execute `uvicorn src.main:app --reload` a partir desta pasta.

Redis é usado para cache de dados públicos e rate limiting por IP. Falhas de cache degradam para o PostgreSQL, preservando a disponibilidade das consultas.
