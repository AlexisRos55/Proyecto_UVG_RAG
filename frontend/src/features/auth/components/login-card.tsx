import type { ReactNode } from "react";
import { motion } from "framer-motion";

import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { fadeSlideUp } from "@/features/auth/animations";

interface LoginCardProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

/**
 * Superficie del formulario: tarjeta blanca sobre el lienzo gris, con la cabecera
 * institucional fija (logotipo + separador + título). Sólo define el contenedor y la
 * jerarquía tipográfica; el contenido lo aporta quien la usa.
 *
 * `--card-spacing` gobierna a la vez el padding y el ritmo vertical del `Card` de
 * shadcn/ui, así que basta redefinirlo para densificar la tarjeta en móvil.
 */
export function LoginCard({ title, subtitle, children }: LoginCardProps) {
  return (
    <motion.div
      variants={fadeSlideUp}
      initial="hidden"
      animate="visible"
      className="w-full max-w-[27.5rem]"
    >
      <Card className="rounded-2xl bg-white shadow-[0_1px_2px_rgb(12_61_91/0.04),0_18px_50px_-20px_rgb(12_61_91/0.22)] ring-1 ring-slate-900/[0.06] [--card-spacing:--spacing(7)] sm:[--card-spacing:--spacing(8)] xl:[--card-spacing:--spacing(9)]">
        <CardContent className="flex flex-col gap-7">
          <header className="flex flex-col gap-5">
            <img
              src="/brand/logo-uvg-altiplano-horizontal-verde.png"
              alt="Universidad del Valle de Guatemala, Campus Altiplano"
              className="h-8 w-auto self-start"
            />
            <Separator className="bg-slate-100" />
            <div className="flex flex-col gap-1.5">
              <h2 className="font-heading text-[1.75rem] leading-tight font-semibold tracking-[-0.025em] text-uvg-navy">
                {title}
              </h2>
              <p className="text-[0.9375rem] leading-6 text-slate-500">{subtitle}</p>
            </div>
          </header>

          {children}
        </CardContent>
      </Card>
    </motion.div>
  );
}
