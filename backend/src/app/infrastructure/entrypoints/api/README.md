# infrastructure/entrypoints/api

Punto de entrada HTTP del sistema (FastAPI). Es la única capa que traduce entre el mundo HTTP y los casos de uso de `application/use_cases`.

```
api/
├── routers/       # Endpoints agrupados por dominio: auth.py, chat.py, admin_documents.py, health.py
├── schemas/       # Modelos Pydantic de request/response (DTOs de transporte HTTP, distintos de application/dto)
└── middlewares/   # Autenticación de sesión, manejo de errores, CORS
```

Reglas:
- Un router nunca contiene lógica de negocio: solo valida la entrada (Pydantic), invoca un caso de uso, y traduce el resultado a una respuesta HTTP.
- Las excepciones de dominio (`domain` exceptions definidas en `shared/exceptions`) se traducen a códigos HTTP apropiados en un manejador de excepciones centralizado, no dispersos en cada router.
- El punto de composición de dependencias (qué adaptador concreto se inyecta en cada caso de uso) vive aquí, típicamente en `main.py` o un módulo de `dependencies.py`.
