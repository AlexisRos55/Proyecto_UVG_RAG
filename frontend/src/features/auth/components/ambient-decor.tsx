import { motion, useReducedMotion } from "framer-motion";

/**
 * Capa atmosférica del panel institucional: retícula de puntos, halos difusos, un anillo
 * fino y líneas diagonales. Es puramente decorativa (`aria-hidden`) y de muy baja opacidad;
 * su función es dar profundidad a la fotografía, no llamar la atención.
 *
 * Con "reducir movimiento" activado los elementos se dibujan igual pero quietos: la textura
 * se conserva y sólo desaparece la animación.
 */
export function AmbientDecor() {
  const prefersReducedMotion = useReducedMotion();

  const drift = (x: number[], y: number[], duration: number) =>
    prefersReducedMotion
      ? undefined
      : {
          x,
          y,
          transition: { duration, repeat: Infinity, repeatType: "mirror" as const, ease: "easeInOut" as const },
        };

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Retícula de puntos, desvanecida hacia los bordes */}
      <div className="absolute inset-0 opacity-[0.14] [background-image:radial-gradient(rgb(255_255_255/0.75)_1px,transparent_1px)] [background-size:26px_26px] [mask-image:radial-gradient(75%_60%_at_45%_30%,black,transparent)]" />

      {/* Halos difusos: aportan el degradado azul que respira detrás del contenido */}
      <motion.div
        className="absolute -top-24 -left-20 size-[26rem] rounded-full bg-uvg-accent/25 blur-[110px]"
        animate={drift([0, 34, 0], [0, 26, 0], 24)}
      />
      <motion.div
        className="absolute -right-24 bottom-[18%] size-[22rem] rounded-full bg-sky-400/20 blur-[110px]"
        animate={drift([0, -28, 0], [0, -22, 0], 28)}
      />

      {/* Anillo fino en rotación muy lenta */}
      <motion.div
        className="absolute -right-32 -bottom-40 size-[34rem] rounded-full border border-white/[0.07]"
        animate={prefersReducedMotion ? undefined : { rotate: 360 }}
        transition={prefersReducedMotion ? undefined : { duration: 140, repeat: Infinity, ease: "linear" }}
      >
        <span className="absolute top-1/2 left-0 size-1.5 -translate-y-1/2 rounded-full bg-white/40" />
      </motion.div>
      <div className="absolute -right-20 -bottom-24 size-[22rem] rounded-full border border-white/[0.06]" />

      {/* Líneas diagonales de encuadre */}
      <div className="absolute inset-y-0 left-[22%] w-px bg-linear-to-b from-transparent via-white/[0.08] to-transparent" />
      <div className="absolute inset-y-0 right-[16%] w-px bg-linear-to-b from-transparent via-white/[0.06] to-transparent" />
    </div>
  );
}
