import { useId, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { MotionConfig } from "framer-motion";

import { Separator } from "@/components/ui/separator";
import { FormAlert } from "@/features/auth/components/form-alert";
import { HeroSection } from "@/features/auth/components/hero-section";
import { InfoPanel } from "@/features/auth/components/info-panel";
import { LoginCard } from "@/features/auth/components/login-card";
import { LoginFooter } from "@/features/auth/components/login-footer";
import { LoginForm } from "@/features/auth/components/login-form";
import { MicrosoftLogo } from "@/features/auth/components/microsoft-logo";
import { MobileBrandBar } from "@/features/auth/components/mobile-brand-bar";
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
  const { login } = useAuth();
  const navigate = useNavigate();
  const [notice, setNotice] = useState<string | null>(null);
  const noticeId = useId();

  const mutation = useMutation<void, unknown, LoginFormValues>({
    mutationFn: (values) => login(values),
    onSuccess: () => navigate("/chat", { replace: true }),
  });

  const errorMessage = mutation.isError
    ? mutation.error instanceof ApiError
      ? mutation.error.message
      : GENERIC_LOGIN_ERROR
    : null;

  const handleSubmit = (values: LoginFormValues) => {
    setNotice(null);
    mutation.mutate(values);
  };

  return (
    <MotionConfig reducedMotion="user">
      {/* `grid-rows-[auto]` y no `grid-rows-1`: la utilidad numérica compila a
          `minmax(0,1fr)`, que elimina el suelo de altura mínima de la fila y recorta el
          panel institucional en pantallas bajas. Una fila `auto` se estira igual hasta
          `min-h-svh` pero crece cuando el contenido no cabe. */}
      <div className="grid min-h-svh grid-rows-[auto_1fr] bg-uvg-canvas lg:grid-cols-[45fr_55fr] lg:grid-rows-[auto]">
        <MobileBrandBar />
        <HeroSection />

        <main className="relative flex min-w-0 items-center justify-center px-5 py-10 sm:px-8 sm:py-12 xl:py-14">
          {/* Textura del lienzo: halo azul superior y retícula muy tenue */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(65%_45%_at_50%_0%,rgb(0_140_54/0.07),transparent_70%)]"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 [background-image:linear-gradient(rgb(15_23_42/0.028)_1px,transparent_1px),linear-gradient(90deg,rgb(15_23_42/0.028)_1px,transparent_1px)] [background-size:44px_44px] [mask-image:radial-gradient(70%_55%_at_50%_45%,black,transparent)]"
          />

          <div className="relative flex w-full flex-col items-center gap-7">
            <LoginCard title="Bienvenido" subtitle="Inicia sesión con tu cuenta institucional.">
              <FormAlert message={errorMessage} />

              <LoginForm
                isPending={mutation.isPending}
                isSuccess={mutation.isSuccess}
                onSubmit={handleSubmit}
                onForgotPassword={() => setNotice(PASSWORD_RESET_NOTICE)}
              />

              <div className="flex items-center gap-3">
                <Separator className="flex-1 bg-slate-200" />
                <span className="text-xs font-medium text-slate-400">o</span>
                <Separator className="flex-1 bg-slate-200" />
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
            </LoginCard>

            <LoginFooter />
          </div>
        </main>
      </div>
    </MotionConfig>
  );
}
