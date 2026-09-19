import { AnimatePresence, motion } from "framer-motion";
import { CloudOff } from "lucide-react";

import { transition } from "@/design-system/motion";

/**
 * Aviso de pérdida de conexión con el servidor.
 *
 * El estado ya se sondeaba (`useBackendStatus`, sobre el mismo `GET /health` del
 * healthcheck de Docker) pero sólo se representaba con un punto de 6 píxeles en
 * una esquina. El resultado era que el compositor seguía pareciendo operativo y
 * el estudiante descubría la caída al enviar y recibir un error.
 *
 * Decir antes lo que va a fallar es más honesto que explicarlo después, así que
 * el aviso aparece en el flujo de lectura. Es una barra tenue, no una alerta
 * roja: no ha ocurrido nada grave, simplemente no se puede consultar ahora.
 */
export function ConnectionNotice({ isOffline }: { isOffline: boolean }) {
  return (
    <AnimatePresence>
      {isOffline && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={transition.base}
          role="status"
          aria-live="polite"
          className="mx-auto w-full max-w-[var(--measure)] shrink-0 px-4 pb-3 sm:px-8"
        >
          <p className="text-caption text-muted-foreground bg-muted/60 flex items-start gap-2.5 rounded-xl px-3.5 py-2.5">
            <CloudOff className="mt-[0.15em] size-3.5 shrink-0" strokeWidth={1.75} />
            <span>
              Sin conexión con el servidor. Puedes seguir leyendo esta conversación, pero las
              consultas nuevas no se enviarán hasta que se restablezca.
            </span>
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
