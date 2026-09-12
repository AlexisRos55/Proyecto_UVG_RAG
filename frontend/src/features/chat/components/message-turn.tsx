import { motion } from "framer-motion";
import { FileText, ShieldAlert, ShieldCheck } from "lucide-react";

import { fadeRise } from "@/design-system/motion";
import { MarkdownContent } from "@/features/chat/components/markdown-content";
import type { MessageDto, SourceReference } from "@/shared/types/api";

/**
 * Un intercambio se compone como una sección de documento, no como dos burbujas:
 * la pregunta es el titular de la sección y la respuesta su cuerpo. La jerarquía
 * tipográfica (peso y tamaño) es lo único que distingue quién habla — no hacen
 * falta avatares, colores ni contenedores.
 */
export function QuestionBlock({ content, isFirst }: { content: string; isFirst: boolean }) {
  return (
    <motion.h2
      variants={fadeRise}
      initial="hidden"
      animate="visible"
      className={`text-title text-foreground ${isFirst ? "" : "mt-16"}`}
    >
      {content}
    </motion.h2>
  );
}

function SourceList({ sources }: { sources: SourceReference[] }) {
  return (
    <div className="mt-8">
      <p className="text-micro text-muted-foreground/55 font-semibold uppercase">Fuentes</p>
      {/* Texto, no botones: abrir el documento todavía no existe en el backend y
          un elemento con aspecto de botón que no hace nada es una promesa falsa. */}
      <ul className="mt-3 space-y-2">
        {sources.map((source) => (
          <li
            key={`${source.document_name}-${source.page_number ?? "n"}`}
            className="text-caption text-muted-foreground flex items-start gap-2.5"
          >
            <FileText className="mt-[0.2em] size-3.5 shrink-0 opacity-50" strokeWidth={1.75} />
            <span>
              {source.document_name}
              {source.page_number != null && (
                <span className="text-muted-foreground/60"> · pág. {source.page_number}</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Señal de verificación como nota al pie, nunca como etiqueta de color. */
function GroundingNote({ isGrounded }: { isGrounded: boolean }) {
  const Icon = isGrounded ? ShieldCheck : ShieldAlert;
  return (
    <p className="text-caption text-muted-foreground/75 mt-6 flex items-start gap-2">
      <Icon className="mt-[0.2em] size-3.5 shrink-0 opacity-60" strokeWidth={1.75} />
      {isGrounded
        ? "Verificado contra los documentos oficiales indexados."
        : "Esta respuesta no pudo fundamentarse en los documentos oficiales indexados."}
    </p>
  );
}

export function AnswerBlock({ message }: { message: Pick<MessageDto, "content" | "is_grounded" | "sources"> }) {
  const hasSources = message.sources.length > 0;

  return (
    <motion.div variants={fadeRise} initial="hidden" animate="visible" className="mt-7">
      <MarkdownContent content={message.content} />

      {hasSources && <SourceList sources={message.sources} />}
      {/* Con fuentes a la vista, repetir "verificado" sería redundante. */}
      {message.is_grounded !== null && !(message.is_grounded && hasSources) && (
        <GroundingNote isGrounded={message.is_grounded} />
      )}
    </motion.div>
  );
}
