import { z } from "zod";

/** Dominio institucional exigido por el backend (ver ADR-0004). */
export const INSTITUTIONAL_EMAIL_DOMAIN = "@uvg.edu.gt";

const institutionalEmail = z
  .string()
  .min(1, "El correo es obligatorio")
  .email("Correo inválido")
  .endsWith(
    INSTITUTIONAL_EMAIL_DOMAIN,
    `Debe ser un correo institucional (${INSTITUTIONAL_EMAIL_DOMAIN})`,
  );

export const credentialsSchema = z.object({
  email: institutionalEmail,
  password: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
});

export type CredentialsFormValues = z.infer<typeof credentialsSchema>;

/**
 * Login se valida aparte del registro: al iniciar sesión no se re-valida la política de
 * longitud de la contraseña (esa regla pertenece al alta de la cuenta) — pedirle "mínimo 8
 * caracteres" a quien ya tiene una cuenta filtra un requisito del servidor y confunde.
 * `rememberMe` no se declara con `.default()` a propósito: eso haría que el tipo de entrada
 * y el de salida difieran, y react-hook-form necesita que coincidan.
 */
export const loginSchema = z.object({
  email: institutionalEmail,
  password: z.string().min(1, "La contraseña es obligatoria"),
  rememberMe: z.boolean(),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
