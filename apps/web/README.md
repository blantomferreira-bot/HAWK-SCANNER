# HAWK SCANNER Web

Dashboard Next.js 15 em Tailwind CSS, com componentes compatíveis com a organização shadcn/ui definida em `components.json`.

## Interface

- Tema escuro premium e layout responsivo para mobile e desktop.
- Sidebar, cabeçalho operacional, cards analíticos, gráfico de momentum, heatmap e ranking filtrável.
- Componentes reutilizáveis em `components/ui` e componentes de produto em `components/dashboard`.

Os dados atuais em `lib/demo-data.ts` permitem renderização independente. Eles serão substituídos pelos endpoints REST em `/api/v1` quando o worker de ingestão estiver ativo.
