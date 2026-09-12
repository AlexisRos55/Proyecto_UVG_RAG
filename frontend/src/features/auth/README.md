# features/auth

Portal de acceso institucional y alta de cuenta con correo `@uvg.edu.gt`. Validación con
React Hook Form + Zod, consistente con la restricción de dominio que el backend aplica
también del lado del servidor (ver [ADR-0004](../../../../docs/adr/0004-institutional-authentication.md)).

## Estructura

| Archivo | Responsabilidad |
| --- | --- |
| `LoginPage.tsx` | Compone el portal: rejilla 45/55, mutación de acceso y mensajería de estado. |
| `RegisterPage.tsx` | Alta de cuenta (alcance mínimo, ver `docs/08-roadmap.md`). |
| `auth-context.tsx` | Sesión en memoria + persistencia. Expone `login(credentials)`. |
| `schemas.ts` | `loginSchema` y `credentialsSchema` (registro). |
| `animations.ts` | Vocabulario de movimiento compartido (Framer Motion). |
| `components/hero-section.tsx` | Panel institucional: fotografía, velo navy, capacidades del asistente. |
| `components/ambient-decor.tsx` | Capa decorativa del panel (retícula, halos, anillos). |
| `components/mobile-brand-bar.tsx` | Sustituye al panel por debajo de `lg`, conservando la marca. |
| `components/login-card.tsx` | Tarjeta blanca: logotipo, separador y jerarquía tipográfica. |
| `components/login-form.tsx` | Formulario de acceso. Emite `{ email, password, rememberMe }`. |
| `components/credentials-form.tsx` | Formulario de registro. Reutiliza los mismos campos. |
| `components/input-field.tsx` | Campo de texto con icono, estados y cableado ARIA del error. |
| `components/password-field.tsx` | `InputField` + alternancia mostrar/ocultar. |
| `components/social-login-button.tsx` | Acceso federado (SSO). |
| `components/form-alert.tsx` | Mensaje a nivel de formulario (error del API o aviso). |
| `components/field-error.tsx` | Mensaje de validación de un campo. |
| `components/info-panel.tsx` | Aviso informativo de baja jerarquía. |
| `components/login-footer.tsx` | Versión y procedencia académica. |

## Decisiones

- **Color.** El manual de marca reserva el verde UVG para el logotipo. La interfaz usa el
  azul marino institucional `#0C3D5B` (tokens `--uvg-navy*`) en las superficies de marca y
  el azul de acción `#2563EB` (`--uvg-accent*`) en todo lo interactivo: CTA, foco y enlaces.
  Los tokens viven en `src/index.css`.
- **`rememberMe` no viaja al API.** El contrato de `POST /auth/login` sólo declara `email` y
  `password`; la casilla decide dónde se guarda la sesión (`localStorage` frente a
  `sessionStorage`), que es una preferencia del cliente.
- **Validación al enviar.** `mode: "onSubmit"` con `reValidateMode: "onChange"`: acusar
  "es obligatorio" por tabular sobre un campo vacío castiga al usuario antes de tiempo.
- **Caminos aún no implementados.** No existe endpoint de recuperación de contraseña ni
  federación con Entra ID. Ambos controles se muestran activos y, al pulsarlos, explican su
  estado en línea; marcarlos con `aria-disabled` y dejarlos operables sería contradictorio
  para quien usa lector de pantalla.
- **Sólo modo claro.** El portal fija su propia paleta y no responde a la variante `.dark`;
  es una superficie de marca, no una pantalla de la aplicación.

Alcance mínimo aceptado por restricción de tiempo: ver `docs/08-roadmap.md`, sección 2.
