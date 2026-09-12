import { motion } from "framer-motion";

import { fadeIn } from "@/features/auth/animations";

/**
 * Cabecera de marca para tablet y móvil, donde `HeroSection` no cabe. La fotografía se
 * conserva sólo como textura tenue detrás del velo navy: se mantiene la identidad
 * institucional sin robarle espacio vertical al formulario.
 */
export function MobileBrandBar() {
  return (
    <motion.header
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      className="relative isolate overflow-hidden bg-uvg-navy-deep px-6 py-7 sm:px-10 lg:hidden"
    >
      <img
        src="/brand/campus-altiplano-bg.jpg"
        alt=""
        aria-hidden="true"
        className="absolute inset-0 -z-10 size-full object-cover object-center opacity-30"
      />
      <div className="absolute inset-0 -z-10 bg-linear-to-r from-uvg-navy-deep/95 via-uvg-navy/90 to-uvg-navy-soft/85" />
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(90%_120%_at_0%_0%,rgb(0_140_54/0.35),transparent_65%)]" />

      <div className="flex flex-col gap-3">
        <img
          src="/brand/logo-uvg-altiplano-horizontal-blanco.png"
          alt="Universidad del Valle de Guatemala, Campus Altiplano"
          className="h-8 w-auto self-start"
        />
        <h1 className="font-heading text-xl leading-tight font-semibold tracking-[-0.02em] text-white">
          Asistente Inteligente UVG
        </h1>
        <p className="max-w-[42ch] text-[0.8125rem] leading-relaxed text-white/65">
          Plataforma institucional basada en Inteligencia Artificial para estudiantes,
          docentes y personal administrativo.
        </p>
      </div>
    </motion.header>
  );
}
