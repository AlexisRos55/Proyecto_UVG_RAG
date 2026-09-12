import type { Transition, Variants } from "framer-motion";

/**
 * Vocabulario de movimiento compartido por el portal de acceso. Se centraliza para que
 * todas las superficies entren con la misma curva y duración: la coherencia del timing es
 * lo que hace que una animación se lea como "de producto" y no como efecto suelto.
 */
export const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

export const softTransition: Transition = { duration: 0.55, ease: EASE_OUT_EXPO };

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: softTransition },
};

export const fadeSlideUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: softTransition },
};

export const fadeSlideRight: Variants = {
  hidden: { opacity: 0, x: -18 },
  visible: { opacity: 1, x: 0, transition: softTransition },
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
  visible: { opacity: 1, height: "auto", transition: { duration: 0.24, ease: EASE_OUT_EXPO } },
  exit: { opacity: 0, height: 0, marginTop: 0, transition: { duration: 0.18 } },
};
