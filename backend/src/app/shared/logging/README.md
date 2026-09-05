# shared/logging

Configuración única de Loguru para todo el backend (formato, nivel, sinks). Se inicializa una sola vez en el punto de composición (`main.py`) y se importa como utilidad transversal.

Cada etapa relevante del pipeline RAG (recuperación, generación, verificación) debe loguear al menos: duración de la operación y, cuando aplique, tokens consumidos — ver NFR-01 y NFR-05 en `docs/03-non-functional-requirements.md`.
