import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Compass, ShieldOff } from "lucide-react";
import { cn } from "cn";

import { BrandLockup } from "@/design-system/brand";
import { fadeRise, stagger } from "@/design-system/motion";

/**
 * Pantallas de estado del sistema.
 *
 * Antes cualquier ruta desconocida redirigía en silencio al chat y un usuario sin
 * permiso era expulsado sin explicación: en ambos casos el usuario acababa en un
 * sitio que no había pedido, sin saber por qué.
 */
function StatusPage({
  icon,
  code,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  code: string;
  title: string;
  description: string;
  action: ReactNode;
}) {
  return (
    <div className="bg-background flex min-h-svh flex-col">
      <header className="px-6 pt-6 sm:px-10">
        <BrandLockup />
      </header>

      <motion.main
        variants={stagger(0.06, 0.05)}
        initial="hidden"
        animate="visible"
        className="flex flex-1 flex-col items-center justify-center px-6 pb-20 text-center"
      >
        <motion.span
          variants={fadeRise}
          className="bg-muted text-muted-foreground flex size-14 items-center justify-center rounded-2xl"
        >
          {icon}
        </motion.span>

        <motion.p
          variants={fadeRise}
          className="text-micro text-text-tertiary mt-7 font-semibold uppercase"
        >
          {code}
        </motion.p>
        <motion.h1 variants={fadeRise} className="text-display text-foreground mt-2">
          {title}
        </motion.h1>
        <motion.p
          variants={fadeRise}
          className="text-body text-muted-foreground mt-4 max-w-md text-balance"
        >
          {description}
        </motion.p>

        <motion.div variants={fadeRise} className="mt-9">
          {action}
        </motion.div>
      </motion.main>
    </div>
  );
}

const actionClass = cn(
  "text-ui bg-primary text-primary-foreground inline-flex items-center rounded-xl px-5 py-2.5 font-medium",
  "transition-opacity hover:opacity-90",
  "focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none",
);

export function NotFoundPage() {
  return (
    <StatusPage
      icon={<Compass className="size-6" strokeWidth={1.75} />}
      code="Error 404"
      title="Esta página no existe."
      description="La dirección que abriste no corresponde a ninguna sección del asistente. Puede que el enlace esté incompleto o haya cambiado."
      action={
        <Link to="/chat" className={actionClass}>
          Volver al asistente
        </Link>
      }
    />
  );
}

export function ForbiddenPage() {
  return (
    <StatusPage
      icon={<ShieldOff className="size-6" strokeWidth={1.75} />}
      code="Acceso restringido"
      title="No tienes permiso."
      description="Esta sección está reservada para cuentas administrativas. Si necesitas gestionar los documentos oficiales, solicita el permiso al equipo del Campus Altiplano."
      action={
        <Link to="/chat" className={actionClass}>
          Volver al asistente
        </Link>
      }
    />
  );
}
