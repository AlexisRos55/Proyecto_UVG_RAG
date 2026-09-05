import { z } from "zod";

export const credentialsSchema = z.object({
  email: z
    .string()
    .min(1, "El correo es obligatorio")
    .email("Correo inválido")
    .endsWith("@uvg.edu.gt", "Debe ser un correo institucional (@uvg.edu.gt)"),
  password: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
});

export type CredentialsFormValues = z.infer<typeof credentialsSchema>;
