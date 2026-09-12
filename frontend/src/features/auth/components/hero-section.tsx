import type { ComponentType } from "react";
import { motion } from "framer-motion";
import { BookOpen, GraduationCap, MessagesSquare, Sparkles } from "lucide-react";

import { AmbientDecor } from "@/features/auth/components/ambient-decor";
import { fadeSlideRight, fadeSlideUp, staggerContainer } from "@/features/auth/animations";

interface Capability {
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  description: string;
}

const CAPABILITIES: readonly Capability[] = [
  { icon: BookOpen, title: "Reglamentos", description: "Normativa vigente" },
  { icon: GraduationCap, title: "Becas", description: "Requisitos y plazos" },
  { icon: MessagesSquare, title: "Consultas inteligentes", description: "Respuestas con fuente" },
  { icon: Sparkles, title: "IA generativa", description: "Búsqueda aumentada" },
];

/**
 * Panel institucional (45% en escritorio). Fotografía real del Campus Altiplano bajo un
 * velo azul marino: la imagen aporta contexto, el velo garantiza el contraste del texto
 * blanco sin depender de qué zona de la foto quede visible al recortar.
 *
 * Oculto por debajo de `lg`; en pantallas pequeñas la marca la sostiene `MobileBrandBar`.
 */
export function HeroSection() {
  return (
    <aside className="relative hidden overflow-hidden bg-uvg-navy-deep lg:flex lg:flex-col lg:justify-between lg:p-10 xl:p-14">
      <img
        src="/brand/campus-altiplano-bg.jpg"
        alt=""
        aria-hidden="true"
        className="absolute inset-0 size-full scale-105 object-cover object-[60%_center]"
      />

      {/* Velo institucional: navy en diagonal + realce verde UVG + viñeta inferior.
          Verde sobre navy es la combinación oficial de la marca. */}
      <div className="absolute inset-0 bg-linear-to-br from-uvg-navy-deep/94 via-uvg-navy/88 to-uvg-navy-soft/78" />
      <div className="absolute inset-0 bg-[radial-gradient(105%_80%_at_10%_6%,rgb(0_140_54/0.3),transparent_58%)]" />
      <div className="absolute inset-0 bg-linear-to-t from-uvg-navy-deep/80 via-transparent to-transparent" />

      <AmbientDecor />

      <motion.div
        variants={staggerContainer(0.09, 0.12)}
        initial="hidden"
        animate="visible"
        className="relative z-10 flex grow flex-col justify-between gap-10 xl:gap-12"
      >
        <motion.header variants={fadeSlideRight} className="flex items-center gap-4">
          <img
            src="/brand/logo-uvg-altiplano-horizontal-blanco.png"
            alt="Universidad del Valle de Guatemala, Campus Altiplano"
            className="h-10 w-auto xl:h-12"
          />
          <span className="rounded-full bg-white/10 px-2.5 py-1 text-[0.6875rem] font-semibold tracking-[0.14em] text-white/80 uppercase ring-1 ring-white/15 backdrop-blur-sm">
            Campus Altiplano
          </span>
        </motion.header>

        {/* motion.div y no div: las variantes sólo se propagan a través de nodos motion. */}
        <motion.div className="flex flex-col gap-7 xl:gap-9">
          <motion.div variants={fadeSlideUp} className="flex flex-col gap-4">
            <span className="inline-flex w-fit items-center gap-2 rounded-full bg-white/[0.08] py-1.5 pr-3.5 pl-2 text-xs font-medium text-white/85 ring-1 ring-white/15 backdrop-blur-sm">
              <Sparkles className="text-uvg-green-masters size-3.5" aria-hidden="true" />
              Plataforma institucional con IA
            </span>
            <h1 className="font-heading max-w-[13ch] text-[2.5rem] leading-[1.06] font-semibold tracking-[-0.03em] text-white xl:text-[3.25rem]">
              Asistente Inteligente UVG
            </h1>
            <p className="max-w-[46ch] text-[1.0625rem] leading-relaxed text-white/70">
              Plataforma institucional basada en Inteligencia Artificial para apoyar a
              estudiantes, docentes y personal administrativo.
            </p>
          </motion.div>

          <motion.ul
            variants={staggerContainer(0.06)}
            className="grid max-w-xl grid-cols-2 gap-3"
          >
            {CAPABILITIES.map(({ icon: Icon, title, description }) => (
              <motion.li
                key={title}
                variants={fadeSlideUp}
                whileHover={{ y: -3 }}
                transition={{ type: "spring", stiffness: 320, damping: 24 }}
                className="flex flex-col gap-2.5 rounded-2xl bg-white/[0.09] p-4 ring-1 ring-white/[0.16] backdrop-blur-md transition-colors duration-300 hover:bg-white/[0.14] hover:ring-white/25"
              >
                <span className="flex size-9 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/10">
                  <Icon className="size-[1.05rem] text-white" strokeWidth={1.75} />
                </span>
                <span className="flex flex-col gap-0.5">
                  <span className="text-sm font-semibold text-white">{title}</span>
                  <span className="text-xs text-white/55">{description}</span>
                </span>
              </motion.li>
            ))}
          </motion.ul>
        </motion.div>
      </motion.div>
    </aside>
  );
}
