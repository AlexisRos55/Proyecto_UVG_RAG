import { useId, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Separator } from "@/components/ui/separator";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { FormAlert } from "@/features/auth/components/form-alert";
import { InfoPanel } from "@/features/auth/components/info-panel";
import { LoginCard } from "@/features/auth/components/login-card";
import { LoginForm } from "@/features/auth/components/login-form";
import { MicrosoftLogo } from "@/features/auth/components/microsoft-logo";
import { SocialLoginButton } from "@/features/auth/components/social-login-button";
import { useAuth } from "@/features/auth/auth-context";
import type { LoginFormValues } from "@/features/auth/schemas";
import { ApiError } from "@/shared/lib/api-client";

/**
 * Estos dos caminos existen en la interfaz pero todavía no en el backend (no hay endpoint de
 * recuperación ni federación con Entra ID). Se muestran deshabilitados y explicados en lugar
 * de ocultarse, para que el portal refleje el alcance previsto del sistema.
 */
const PASSWORD_RESET_NOTICE =
  "El restablecimiento de contraseña se gestiona con el equipo de soporte académico del Campus Altiplano.";
const MICROSOFT_SSO_NOTICE =
  "El acceso con Microsoft 365 aún no está habilitado. Ingresa con tu correo institucional y contraseña.";

const GENERIC_LOGIN_ERROR = "No se pudo iniciar sesión. Inténtalo de nuevo en unos momentos.";

/** Portal de acceso institucional: panel de marca (45%) + formulario centrado (55%). */
export function LoginPage() {
  const { login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notice, setNotice] = useState<string | null>(null);
  const noticeId = useId();

  // Destino guardado por la ruta protegida: se devuelve al usuario donde iba.
  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/chat";

  const mutation = useMutation<void, unknown, LoginFormValues>({
    mutationFn: (values) => login(values),
    onSuccess: () => navigate(redirectTo, { replace: true }),
  });

  const errorMessage = mutation.isError
    ? mutation.error instanceof ApiError
      ? mutation.error.message
      : GENERIC_LOGIN_ERROR
    : null;

  // Se explica por qué se pide iniciar sesión otra vez, en vez de devolver al
  // usuario a un formulario vacío sin motivo aparente.
  const expiredNotice = sessionExpired
    ? "Tu sesión expiró por seguridad. Vuelve a iniciar sesión para continuar."
    : null;

  const handleSubmit = (values: LoginFormValues) => {
    setNotice(null);
    mutation.mutate(values);
  };

  return (
    <AuthLayout>
            <LoginCard title="Bienvenido" subtitle="Inicia sesión con tu cuenta institucional.">
              <FormAlert message={errorMessage} />
              {!errorMessage && <FormAlert message={expiredNotice} tone="info" />}

              <LoginForm
                isPending={mutation.isPending}
                isSuccess={mutation.isSuccess}
                onSubmit={handleSubmit}
                onForgotPassword={() => setNotice(PASSWORD_RESET_NOTICE)}
              />

              <div className="flex items-center gap-3">
                <Separator className="flex-1 bg-border" />
                <span className="text-caption font-medium text-text-tertiary">o</span>
                <Separator className="flex-1 bg-border" />
              </div>

              <div className="flex flex-col gap-4">
                <SocialLoginButton
                  icon={<MicrosoftLogo className="size-full" />}
                  label="Ingresar con Microsoft"
                  describedBy={notice ? noticeId : undefined}
                  onClick={() => setNotice(MICROSOFT_SSO_NOTICE)}
                />

                <FormAlert id={noticeId} message={notice} tone="info" />

                <InfoPanel>
                  Solo pueden ingresar usuarios autorizados por la Universidad del Valle de
                  Guatemala.
                </InfoPanel>
              </div>

              {/* Antes /register era inalcanzable: solo existía el enlace inverso. */}
              <p className="text-caption text-muted-foreground text-center">
                ¿Aún no tienes cuenta?{" "}
                <Link
                  to="/register"
                  className="text-primary hover:text-uvg-accent-strong focus-visible:ring-ring rounded font-medium underline-offset-4 transition-colors hover:underline focus-visible:ring-2 focus-visible:outline-none"
                >
                  Crear una
                </Link>
              </p>
      </LoginCard>
    </AuthLayout>
  );
}
