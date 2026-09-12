import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Info } from "lucide-react";
import { cn } from "cn";

import { collapseFade } from "@/features/auth/animations";

type AlertTone = "error" | "info";

interface FormAlertProps {
  /** Mensaje a mostrar. `null` cuando no hay nada pendiente de comunicar. */
  message: string | null;
  tone?: AlertTone;
  /** Permite que el control que originó el mensaje lo referencie con `aria-describedby`. */
  id?: string;
}

const TONE_STYLES: Record<AlertTone, { container: string; icon: string; text: string }> = {
  error: {
    container: "bg-destructive/[0.06] ring-destructive/15",
    icon: "text-destructive",
    text: "text-destructive",
  },
  info: {
    container: "bg-uvg-accent-soft ring-uvg-accent/15",
    icon: "text-uvg-accent",
    text: "text-slate-600",
  },
};

/**
 * Mensaje a nivel de formulario (credenciales inválidas, servicio no disponible). Se muestra
 * en línea dentro de la tarjeta y no como notificación flotante: pertenece al formulario y
 * debe seguir visible mientras el usuario corrige.
 *
 * `aria-live` sube a "assertive" sólo en los errores; un aviso informativo no debe
 * interrumpir a un lector de pantalla a mitad de frase.
 */
export function FormAlert({ message, tone = "error", id }: FormAlertProps) {
  const styles = TONE_STYLES[tone];
  const Icon = tone === "error" ? AlertTriangle : Info;

  return (
    <AnimatePresence initial={false}>
      {message ? (
        <motion.div
          key={message}
          variants={collapseFade}
          initial="hidden"
          animate="visible"
          exit="exit"
          className="overflow-hidden"
        >
          <div
            id={id}
            role={tone === "error" ? "alert" : "status"}
            aria-live={tone === "error" ? "assertive" : "polite"}
            className={cn(
              "flex items-start gap-2.5 rounded-xl px-3.5 py-3 ring-1",
              styles.container,
            )}
          >
            <Icon className={cn("mt-px size-4 shrink-0", styles.icon)} aria-hidden="true" />
            <p className={cn("text-[0.8125rem] leading-5 font-medium", styles.text)}>{message}</p>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
