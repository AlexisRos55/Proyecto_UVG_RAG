import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown } from "lucide-react";

import { transition } from "@/design-system/motion";

/**
 * Botón para volver al final del hilo.
 *
 * Es la contrapartida de haber dejado de arrastrar al usuario hacia abajo: si el
 * hilo ya no se mueve solo cuando estás leyendo más arriba, hace falta una forma
 * explícita de regresar. Aparece únicamente cuando estás lejos del final, que es
 * el único momento en que significa algo.
 *
 * Va centrado sobre el compositor, no anclado a una esquina: es la acción que
 * devuelve al punto de escritura y pertenece a ese eje.
 */
export function ScrollToBottom({ show, onClick }: { show: boolean; onClick: () => void }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.button
          type="button"
          onClick={onClick}
          initial={{ opacity: 0, y: 6, scale: 0.94 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 6, scale: 0.94 }}
          whileTap={{ scale: 0.92 }}
          transition={transition.spring}
          aria-label="Ir al final de la conversación"
          className="bg-surface-raised text-muted-foreground hover:text-foreground shadow-lifted ring-hairline focus-visible:ring-ring absolute bottom-3 left-1/2 z-10 flex size-9 -translate-x-1/2 items-center justify-center rounded-full ring-1 transition-colors duration-150 ease-soft focus-visible:ring-2 focus-visible:outline-none"
        >
          <ArrowDown className="size-4" strokeWidth={2} />
        </motion.button>
      )}
    </AnimatePresence>
  );
}
