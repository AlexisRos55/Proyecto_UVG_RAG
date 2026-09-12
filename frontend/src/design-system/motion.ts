import type { Transition, Variants } from "framer-motion";

/**
 * Lenguaje de movimiento de UVG AI.
 *
 * Un único juego de curvas y duraciones para toda la aplicación: si cada
 * componente inventa su propia animación, el conjunto se siente ensamblado.
 * `standard` es la curva de macOS/iOS (acelera rápido, frena largo), que es lo
 * que produce la sensación de aplicación nativa.
 */

type Easing = [number, number, number, number];

export const EASE_STANDARD: Easing = [0.32, 0.72, 0, 1];
export const EASE_SOFT: Easing = [0.22, 1, 0.36, 1];

export const transition = {
  /** Hover, focus, cambios de color. Imperceptible pero no instantáneo. */
  micro: { duration: 0.15, ease: EASE_SOFT },
  /** Entrada de elementos, cambios de estado visibles. */
  base: { duration: 0.3, ease: EASE_STANDARD },
  /** Entradas protagonistas: pantalla de bienvenida, primer render. */
  slow: { duration: 0.6, ease: EASE_STANDARD },
  /** Elementos que responden al dedo/cursor: botón de envío, paneles. */
  spring: { type: "spring", stiffness: 420, damping: 34, mass: 0.9 },
} satisfies Record<string, Transition>;

/** Entrada por defecto: aparece subiendo unos pocos píxeles. Nunca desplazamientos largos. */
export const fadeRise: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: transition.base },
};

export const fade: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transition.base },
  exit: { opacity: 0, transition: transition.micro },
};

/** Contenedor que escalona la entrada de sus hijos (listas, sugerencias). */
export const stagger = (gap = 0.055, delayChildren = 0.05): Variants => ({
  hidden: {},
  visible: { transition: { staggerChildren: gap, delayChildren } },
});
