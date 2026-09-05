# shared

Código reutilizado por más de una feature:

- `components/`: componentes de UI basados en shadcn/ui (Tailwind CSS). Componentes específicos de una sola feature viven dentro de esa feature, no aquí.
- `hooks/`: hooks de React reutilizables (p. ej. `useSession`).
- `lib/`: cliente HTTP (fetch/axios configurado con la URL base del backend) y configuración del `QueryClient` de TanStack Query.
- `types/`: tipos TypeScript que reflejan los contratos de la API del backend (DTOs), compartidos entre features.
