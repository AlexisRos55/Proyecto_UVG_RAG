import { motion, useReducedMotion } from "framer-motion";

import { transition } from "@/design-system/motion";

/**
 * Barrido de luz sobre el texto (el patrón de Apple Intelligence), en lugar de
 * los tres puntos saltando: comunica trabajo en curso sin introducir un elemento
 * de interfaz nuevo en el lienzo.
 *
 * Se anuncia con `role="status"` para que un lector de pantalla informe de que
 * el sistema está trabajando — antes el usuario no vidente no recibía ninguna
 * señal entre el envío y la respuesta. Y con `prefers-reduced-motion` el
 * barrido se detiene: el texto sigue estando, solo deja de animarse.
 */
export function ThinkingIndicator() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.p
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={transition.base}
      className="mt-7"
      role="status"
      aria-live="polite"
    >
      <motion.span
        className="text-body bg-[linear-gradient(100deg,var(--muted-foreground)_35%,var(--foreground)_50%,var(--muted-foreground)_65%)] bg-[length:220%_100%] bg-clip-text text-transparent"
        animate={prefersReducedMotion ? undefined : { backgroundPosition: ["180% 0%", "-80% 0%"] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
      >
        Consultando la normativa…
      </motion.span>
    </motion.p>
  );
}
