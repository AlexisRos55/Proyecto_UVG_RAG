# ADR-0019: Modo invitado — un rol más del modelo de usuarios

**Estado:** Aceptado. Extiende [ADR-0004](0004-institutional-authentication.md) (la autenticación institucional no cambia) y [ADR-0008](0008-admin-panel-scope.md) (el panel administrativo sigue reservado al rol administrador).

**Fecha:** 2026-10-09

## Contexto

En la presentación del proyecto surgió un requerimiento: personas sin correo institucional también deben poder usar el asistente. Por ejemplo, aspirantes, padres de familia y visitantes interesados en estudiar.

Hasta ahora solo se podía entrar con una cuenta `@uvg.edu.gt`. Además, la conversación depende del usuario:

- cada conversación pertenece a un usuario (`conversations.user_id`, clave foránea `NOT NULL`);
- la memoria conversacional (ADR-0015 a ADR-0018) se reconstruye a partir de los mensajes guardados.

## Decisión

1. **El invitado es un usuario más**, con el rol `GUEST` y sin credenciales (correo y contraseña nulos).
   - La entidad `User` exige que solo un invitado pueda carecer de credenciales.
   - La base de datos lo garantiza con la restricción `ck_users_credentials_unless_guest`.
   - Así, el chat, su memoria y cada comprobación de autorización funcionan igual que para cualquier rol. No hay un flujo paralelo.
2. **`POST /auth/guest`** abre una sesión temporal sin pedir datos (`StartGuestSessionUseCase`).
   - Emite el mismo token JWT que el resto de sesiones.
   - El rol viaja en el token y se vuelve a leer de la base de datos en cada petición.
3. **Autorización sin cambios.** Las rutas del panel administrativo ya exigen `require_admin`, que rechaza a cualquier usuario que no sea administrador; un invitado nunca lo es.
4. **La conversación sabe quién escribe.**
   - `AnswerQueryRequest.is_guest` llega desde la ruta del chat.
   - Si un invitado pide datos personales, se le dice que esa información está en los sistemas de la universidad, solo para cuentas institucionales.
   - El resto de la conversación es idéntica: búsqueda, evidencia y voz.
5. **Retención acotada.** Cada nueva sesión de invitado elimina las de invitados creados hace más de `guest_retention_days` (7 días, el mismo plazo que el olvido de la memoria conversacional). El borrado en cascada se lleva sus conversaciones. No hace falta ningún planificador y los datos de visitantes no se acumulan.
6. **Frontend.**
   - El login ofrece «Continuar como invitado», junto al acceso institucional.
   - El chat muestra la insignia «Invitado» y un aviso discreto.
   - La sesión del invitado vive en `sessionStorage`: no se recuerda entre visitas.

## Alternativas consideradas

- **Invitado sin fila en la base de datos** (solo en el token). Se descartó: obligaba a un flujo de conversación paralelo sin persistencia, y el invitado perdía la memoria conversacional.
- **Invitado con un correo ficticio** («invitado-…@guest»). Se descartó porque mete datos falsos en la tabla de usuarios y rompe la invariante del correo institucional.
- **Un rol nuevo con su propio sistema de permisos.** Se descartó por innecesario: la única restricción adicional es lo que ya hace `require_admin`.

## Consecuencias

- **Positivas:**
  - los usuarios externos usan el asistente sin registrarse;
  - un solo flujo de autenticación, conversación y autorización;
  - integridad garantizada también en la base de datos;
  - los datos de visitantes no se acumulan.
- **Negativas y riesgos:**
  - `POST /auth/guest` no requiere credenciales, así que cada llamada crea una fila (purgada a los 7 días) y permite conversar con el modelo, con su costo;
  - hoy no hay límite de peticiones. La exposición es comparable a la de `/auth/register`, que tampoco verifica el correo. Antes de un despliegue público conviene limitar la tasa por IP en el proxy (nginx).
- **Migración:** `c4e8a1f0b2d7_guest_users`. Vuelve nulos `email` y `password_hash` y agrega la restricción. Es reversible: al revertir, primero elimina a los invitados.
