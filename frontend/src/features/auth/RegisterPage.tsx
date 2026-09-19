import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { AuthLayout } from "@/features/auth/components/auth-layout";
import { CredentialsForm } from "@/features/auth/components/credentials-form";
import { FormAlert } from "@/features/auth/components/form-alert";
import { InfoPanel } from "@/features/auth/components/info-panel";
import { LoginCard } from "@/features/auth/components/login-card";
import { useAuth } from "@/features/auth/auth-context";
import type { CredentialsFormValues } from "@/features/auth/schemas";
import { ApiError } from "@/shared/lib/api-client";

const GENERIC_REGISTER_ERROR = "No se pudo completar el registro. Inténtalo de nuevo.";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: (values: CredentialsFormValues) => register(values.email, values.password),
    onSuccess: () => navigate("/chat", { replace: true }),
  });

  // El error se muestra dentro de la tarjeta, junto al formulario que lo produjo,
  // y no como aviso flotante en una esquina: "correo ya registrado" pertenece al
  // campo, no al borde de la pantalla.
  const errorMessage = mutation.isError
    ? mutation.error instanceof ApiError
      ? mutation.error.message
      : GENERIC_REGISTER_ERROR
    : null;

  return (
    <AuthLayout>
      <LoginCard
        title="Crear cuenta"
        subtitle="Regístrate con tu correo institucional para comenzar."
      >
        <FormAlert message={errorMessage} />

        <CredentialsForm
          submitLabel="Crear cuenta"
          pendingLabel="Creando cuenta…"
          isPending={mutation.isPending}
          onSubmit={(values) => mutation.mutate(values)}
        />

        <InfoPanel>
          Solo se admiten correos del dominio institucional @uvg.edu.gt.
        </InfoPanel>

        <p className="text-caption text-muted-foreground text-center">
          ¿Ya tienes cuenta?{" "}
          <Link
            to="/login"
            className="text-primary hover:text-uvg-accent-strong focus-visible:ring-ring rounded font-medium underline-offset-4 transition-colors hover:underline focus-visible:ring-2 focus-visible:outline-none"
          >
            Inicia sesión
          </Link>
        </p>
      </LoginCard>
    </AuthLayout>
  );
}
