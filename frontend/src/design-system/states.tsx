import type { ComponentType, ReactNode } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, RotateCw, WifiOff } from "lucide-react";
import { cn } from "@/design-system/cn";

import { fadeRise, transition } from "@/design-system/motion";
import { ApiError } from "@/shared/lib/api-client";

/**
 * Vacío, cargando y error son tres estados distintos y deben *verse* distintos.
 *
 * El panel administrativo los confundía: cuando la petición fallaba no dibujaba
 * nada, y "no hay documentos" era indistinguible de "no pudimos preguntarlo".
 * Estos tres componentes existen para que esa confusión no pueda repetirse en
 * ninguna pantalla.
 */

interface StateShellProps {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  compact?: boolean;
}

function StateShell({ icon, title, description, action, className, compact }: StateShellProps) {
  return (
    <motion.div
      variants={fadeRise}
      initial="hidden"
      animate="visible"
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "gap-3 py-10" : "gap-4 py-16",
        className,
      )}
    >
      {icon}
      <div className="flex flex-col gap-1.5">
        <p className="text-heading text-foreground">{title}</p>
        {description && (
          <p className="text-ui text-muted-foreground max-w-sm text-balance">{description}</p>
        )}
      </div>
      {action}
    </motion.div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  compact,
}: {
  icon?: ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <StateShell
      compact={compact}
      icon={
        Icon && (
          <span className="bg-muted text-muted-foreground flex size-11 items-center justify-center rounded-full">
            <Icon className="size-5" strokeWidth={1.75} />
          </span>
        )
      }
      title={title}
      description={description}
      action={action}
    />
  );
}

/**
 * Traduce un fallo a algo accionable. Distingue el problema de red del fallo del
 * servidor porque la acción del usuario es distinta en cada caso.
 */
export function ErrorState({
  error,
  onRetry,
  compact,
}: {
  error: unknown;
  onRetry?: () => void;
  compact?: boolean;
}) {
  const isNetwork =
    error instanceof ApiError && (error.kind === "network" || error.kind === "timeout");
  const message =
    error instanceof ApiError ? error.message : "Ocurrió un problema al cargar la información.";
  const Icon = isNetwork ? WifiOff : AlertTriangle;

  return (
    <StateShell
      compact={compact}
      icon={
        <span className="bg-destructive/10 text-destructive flex size-11 items-center justify-center rounded-full">
          <Icon className="size-5" strokeWidth={1.75} />
        </span>
      }
      title={isNetwork ? "Sin conexión con el servidor" : "No se pudo cargar"}
      description={message}
      action={
        onRetry && (
          <motion.button
            type="button"
            onClick={onRetry}
            whileTap={{ scale: 0.97 }}
            transition={transition.spring}
            className={cn(
              "text-ui ring-border hover:bg-muted mt-1 inline-flex items-center gap-2 rounded-xl px-3.5 py-2 font-medium ring-1",
              "focus-visible:ring-ring transition-colors focus-visible:ring-2 focus-visible:outline-none",
            )}
          >
            <RotateCw className="size-3.5" strokeWidth={2} />
            Reintentar
          </motion.button>
        )
      }
    />
  );
}

/** Barra de carga por contenido: mantiene la forma de lo que va a aparecer. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("bg-muted animate-pulse rounded-md", className)} aria-hidden="true" />;
}

export function LoadingState({ label = "Cargando…", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="flex flex-col gap-3 py-2" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-center gap-3">
          <Skeleton className="size-9 shrink-0 rounded-lg" />
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <Skeleton className="h-3.5 w-[min(22rem,70%)]" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}
