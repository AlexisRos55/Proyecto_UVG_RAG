import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Copy, FileText, ShieldAlert, ShieldCheck } from "lucide-react";

import { IconButton } from "@/design-system/icon-button";
import { fadeRise } from "@/design-system/motion";
import { MarkdownContent } from "@/features/chat/components/markdown-content";
import { documentDisplayName } from "@/shared/lib/document-name";
import type { MessageDto, SourceReference, VerificationConfidence } from "@/shared/types/api";

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
      <p className="text-micro text-text-tertiary font-semibold uppercase">Fuentes</p>
      {/* Texto, no botones: abrir el documento todavía no existe en el backend y
          un elemento con aspecto de botón que no hace nada es una promesa falsa. */}
      <ul className="mt-3 space-y-2">
        {/* El índice forma parte de la clave: el mismo documento puede citarse dos
            veces (fragmentos distintos de la misma página) y el par nombre+página
            no es único. */}
        {sources.map((source, index) => (
          <li
            key={`${index}-${source.document_name}-${source.page_number ?? "n"}`}
            className="text-caption text-muted-foreground flex items-start gap-2.5"
          >
            <FileText className="mt-[0.2em] size-3.5 shrink-0" strokeWidth={1.75} />
            <span>
              {/* Parte del corpus llegó con los acentos rotos; se repara al mostrar
                  para que la cita no desmienta visualmente su propia trazabilidad. */}
              {documentDisplayName(source.document_name)}
              {source.page_number != null && (
                <span className="text-text-tertiary"> · pág. {source.page_number}</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Señal de verificación como nota al pie, nunca como etiqueta de color.
 *
 * Cuando la respuesta está fundamentada, matiza además con la confianza que el
 * modelo se autoasignó durante la verificación. Ese dato se calculaba, se
 * persistía y llegaba hasta aquí desde el principio, pero ningún componente lo
 * mostraba. Se etiqueta como autoevaluación —que es lo que es— y no como una
 * probabilidad calibrada.
 */
function GroundingNote({
  isGrounded,
  confidence,
}: {
  isGrounded: boolean;
  confidence: VerificationConfidence | null;
}) {
  const Icon = isGrounded ? ShieldCheck : ShieldAlert;

  const text = !isGrounded
    ? "Esta respuesta no pudo fundamentarse en los documentos oficiales indexados."
    : confidence === "low"
      ? "Verificado contra los documentos oficiales, aunque la cobertura es parcial."
      : confidence === "medium"
        ? "Verificado contra los documentos oficiales, con algunos matices."
        : "Verificado contra los documentos oficiales indexados.";

  return (
    <p className="text-caption text-muted-foreground mt-6 flex items-start gap-2">
      <Icon className="mt-[0.2em] size-3.5 shrink-0" strokeWidth={1.75} />
      {text}
    </p>
  );
}

/** Copiar la respuesta al portapapeles, con confirmación en el propio control. */
function CopyAnswer({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Sin permiso de portapapeles (contexto no seguro): el usuario todavía puede
      // seleccionar el texto a mano, así que no se le interrumpe con un error.
    }
  };

  return (
    <IconButton
      size="sm"
      label={copied ? "Respuesta copiada" : "Copiar respuesta"}
      onClick={() => void copy()}
    >
      {copied ? (
        <Check className="text-primary size-4" strokeWidth={2.25} />
      ) : (
        <Copy className="size-4" strokeWidth={1.75} />
      )}
    </IconButton>
  );
}

export function AnswerBlock({
  message,
}: {
  message: Pick<MessageDto, "content" | "is_grounded" | "confidence" | "sources">;
}) {
  const hasSources = message.sources.length > 0;

  return (
    <motion.div variants={fadeRise} initial="hidden" animate="visible" className="group/answer mt-7">
      <MarkdownContent content={message.content} />

      {hasSources && <SourceList sources={message.sources} />}
      {/* Con fuentes a la vista y confianza alta, repetir "verificado" es redundante:
          las propias fuentes ya lo dicen. La nota reaparece cuando el modelo declaró
          cobertura parcial, que es justo cuando el matiz importa. */}
      {message.is_grounded !== null &&
        !(message.is_grounded && hasSources && message.confidence === "high") && (
          <GroundingNote isGrounded={message.is_grounded} confidence={message.confidence} />
        )}

      {/* Aparece al enfocar o pasar el cursor: disponible sin ocupar sitio fijo. */}
      <div className="mt-4 flex items-center gap-1 transition-opacity duration-150 sm:opacity-0 sm:group-focus-within/answer:opacity-100 sm:group-hover/answer:opacity-100">
        <CopyAnswer content={message.content} />
      </div>
    </motion.div>
  );
}
