# Frontend — Asistente Virtual RAG (UVG Altiplano)

React + TypeScript + Vite, organizado por features (screaming architecture) en vez de por tipo técnico de archivo.

## Estructura

```
src/
├── app/               # Bootstrapping: enrutamiento, providers globales (QueryClient, contexto de sesión)
├── features/
│   ├── auth/          # Login (institucional @uvg.edu.gt)
│   ├── chat/          # Interfaz conversacional del estudiante
│   └── admin/         # Panel administrativo (prioridad baja, ver ADR-0008 en docs/)
└── shared/
    ├── components/    # Componentes de UI reutilizables (basados en shadcn/ui)
    ├── hooks/         # Hooks reutilizables entre features
    ├── lib/           # Cliente HTTP, configuración de TanStack Query
    └── types/         # Tipos TypeScript compartidos (contratos con el backend)
```

## Principios

- Cada feature es autocontenida: sus propios componentes, hooks y llamadas a la API viven dentro de su carpeta.
- `shared/` solo contiene lo que realmente se usa en más de una feature — evita que todo termine ahí "por si acaso".
- Los formularios usan React Hook Form + Zod; el esquema de validación de un formulario es la fuente de verdad de su forma de datos.
- El estado de servidor (datos que vienen del backend) se maneja con TanStack Query, no con estado local duplicado.

## Estado actual

Implementado: autenticación (login/registro), chat con indicador de escritura y badge de fundamentación (grounded/no grounded), panel administrativo de documentos (subir/listar/eliminar/reindexar). Build de producción (`npm run build`) y lint (`npm run lint`) verificados sin errores.

Componentes de UI generados con el CLI de shadcn/ui (preset "Nova", Tailwind CSS v4) en `src/components/ui/`; usan el paquete `cn` para el merge de clases en vez de un `lib/utils.ts` propio (convención de este preset).

## Comandos

```bash
npm install
npm run dev       # servidor de desarrollo (http://localhost:5173)
npm run build     # build de producción (tsc -b && vite build)
npm run lint      # ESLint
```

Requiere `VITE_API_BASE_URL` (ver `.env.example`) apuntando al backend.
