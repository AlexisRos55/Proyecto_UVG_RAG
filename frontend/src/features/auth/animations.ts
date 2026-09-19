import type { Variants } from "framer-motion";

import { EASE_SOFT, transition } from "@/design-system/motion";

/**
 * Composiciones de entrada del portal de acceso.
 *
 * Las **curvas** ya no se definen aquí. Este archivo declaraba su propio
 * `EASE_OUT_EXPO = [0.16, 1, 0.3, 1]` y una duración de 0.55s, en paralelo al
 * `EASE_SOFT = [0.22, 1, 0.36, 1]` y los 0.6s del design system: dos lenguajes
 * de movimiento casi idénticos pero distintos, conviviendo en el mismo
 * producto. Eso es justo lo que hace que una aplicación se sienta ensamblada a
 * partir de piezas en lugar de diseñada.
 *
 * Lo que sí es propio del portal son las composiciones: qué entra desde dónde.
 * Eso se queda.
 */

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transition.slow },
};

export const fadeSlideUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: transition.slow },
};

export const fadeSlideRight: Variants = {
  hidden: { opacity: 0, x: -18 },
  visible: { opacity: 1, x: 0, transition: transition.slow },
};

/** Contenedor que escalona la entrada de sus hijos (usar con las variantes de arriba). */
export function staggerContainer(staggerChildren = 0.07, delayChildren = 0.05): Variants {
  return {
    hidden: {},
    visible: { transition: { staggerChildren, delayChildren } },
  };
}

/** Colapso vertical usado por los mensajes de error y las alertas en línea. */
export const collapseFade: Variants = {
  hidden: { opacity: 0, height: 0, marginTop: 0 },
  visible: { opacity: 1, height: "auto", transition: { duration: 0.24, ease: EASE_SOFT } },
  exit: { opacity: 0, height: 0, marginTop: 0, transition: { duration: 0.18, ease: EASE_SOFT } },
};
