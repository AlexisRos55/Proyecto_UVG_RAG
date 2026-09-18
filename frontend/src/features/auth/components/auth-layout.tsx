import type { ReactNode } from "react";
import { MotionConfig } from "framer-motion";

import { HeroSection } from "@/features/auth/components/hero-section";
import { LoginFooter } from "@/features/auth/components/login-footer";
import { MobileBrandBar } from "@/features/auth/components/mobile-brand-bar";

/**
 * Armazón único del portal de autenticación.
 *
 * Acceso y registro son dos estados de la misma superficie, no dos páginas con
 * dos autores. Antes el registro era una tarjeta genérica flotando en el vacío:
 * el usuario nuevo —el único que no conoce el producto— recibía la versión sin
 * diseñar, y quien ya lo conocía recibía la cuidada.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      {/* `grid-rows-[auto]` y no `grid-rows-1`: la utilidad numérica compila a
          `minmax(0,1fr)`, que elimina el suelo de altura mínima de la fila y recorta el
          panel institucional en pantallas bajas. Una fila `auto` se estira igual hasta
          `min-h-svh` pero crece cuando el contenido no cabe. */}
      <div className="bg-uvg-canvas grid min-h-svh grid-rows-[auto_1fr] lg:grid-cols-[45fr_55fr] lg:grid-rows-[auto]">
        <MobileBrandBar />
        <HeroSection />

        <main className="relative flex min-w-0 items-center justify-center px-5 py-10 sm:px-8 sm:py-12 xl:py-14">
          {/* Textura del lienzo: halo verde superior y retícula muy tenue. Ambas
              derivadas de tokens, para que acompañen al modo oscuro. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(65%_45%_at_50%_0%,color-mix(in_oklab,var(--primary)_10%,transparent),transparent_70%)]"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 [background-image:linear-gradient(color-mix(in_oklab,var(--foreground)_4%,transparent)_1px,transparent_1px),linear-gradient(90deg,color-mix(in_oklab,var(--foreground)_4%,transparent)_1px,transparent_1px)] [background-size:44px_44px] [mask-image:radial-gradient(70%_55%_at_50%_45%,black,transparent)]"
          />

          <div className="relative flex w-full flex-col items-center gap-7">
            {children}
            <LoginFooter />
          </div>
        </main>
      </div>
    </MotionConfig>
  );
}
