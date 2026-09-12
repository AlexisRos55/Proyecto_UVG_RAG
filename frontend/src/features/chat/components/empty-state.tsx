import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

import { BrandGlyph } from "@/design-system/brand";
import { fadeRise, stagger, transition } from "@/design-system/motion";

const SUGGESTIONS = [
  "¿Cuál es el reglamento de inscripción?",
  "¿Qué becas y beneficios ofrece la universidad?",
  "¿Qué cubre el seguro estudiantil?",
  "¿Cuáles son los requisitos de graduación?",
] as const;

interface EmptyStateProps {
  userName: string;
  onSelect: (question: string) => void;
}

/**
 * Pantalla de bienvenida al estilo de una aplicación nativa: un saludo enorme,
 * mucho aire y sugerencias como líneas de texto. Sin tarjetas, sin iconos
 * enmarcados, sin bordes — la interfaz casi desaparece.
 */
export function EmptyState({ userName, onSelect }: EmptyStateProps) {
  return (
    <motion.div
      variants={stagger(0.07, 0.08)}
      initial="hidden"
      animate="visible"
      className="mx-auto flex min-h-full w-full max-w-[var(--measure)] flex-col items-center justify-center px-6 py-16 text-center"
    >
      <motion.div
        variants={fadeRise}
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }}
        className="relative"
      >
        {/* Halo difuso: da presencia al símbolo sin necesidad de encerrarlo en un
            contenedor. Es lo que sostiene el centro de la pantalla vacía. */}
        <div
          className="from-primary/30 pointer-events-none absolute -inset-12 rounded-full bg-radial from-0% via-transparent via-55% to-transparent blur-3xl"
          aria-hidden="true"
        />
        <BrandGlyph className="relative size-12" />
      </motion.div>

      <motion.h1 variants={fadeRise} className="text-display text-foreground mt-9">
        {userName ? `Hola, ${userName}.` : "Hola."}
      </motion.h1>
      <motion.p variants={fadeRise} className="text-title text-muted-foreground/80 mt-3">
        Bienvenido al Asistente Inteligente <span className="text-primary">UVG</span>
      </motion.p>
      <motion.p
        variants={fadeRise}
        className="text-body text-muted-foreground/65 mt-4 max-w-md text-balance"
      >
        Consulta reglamentos, beneficios, procesos académicos y documentación oficial mediante
        Inteligencia Artificial.
      </motion.p>

      <motion.div variants={fadeRise} className="mt-12 w-full max-w-lg">
        {SUGGESTIONS.map((question) => (
          <motion.button
            key={question}
            type="button"
            onClick={() => onSelect(question)}
            whileTap={{ scale: 0.99 }}
            transition={transition.spring}
            className="group hover:bg-foreground/[0.035] relative flex w-full items-center justify-between gap-5 rounded-xl px-4 py-3.5 text-left transition-colors duration-150 ease-soft"
          >
            {/* Marca verde que aparece al pasar el cursor: el mismo indicador que
                señala la conversación activa en el panel lateral. */}
            <span
              className="bg-primary absolute top-1/2 left-0 h-5 w-0.5 -translate-y-1/2 rounded-full opacity-0 transition-opacity duration-200 group-hover:opacity-100"
              aria-hidden="true"
            />
            <span className="text-body text-foreground/80 group-hover:text-foreground transition-colors">
              {question}
            </span>
            <ArrowUpRight
              className="text-primary size-4 shrink-0 opacity-0 transition-opacity duration-150 group-hover:opacity-80"
              strokeWidth={1.75}
            />
          </motion.button>
        ))}
      </motion.div>

      <motion.p
        variants={fadeRise}
        className="text-caption text-muted-foreground/55 mt-14 max-w-sm leading-relaxed"
      >
        Las respuestas se generan únicamente a partir de documentos oficiales indexados de la
        Universidad del Valle de Guatemala, Campus Altiplano.
      </motion.p>
    </motion.div>
  );
}
