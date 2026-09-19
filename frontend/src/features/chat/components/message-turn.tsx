import { memo, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import {
  BookMarked,
  CalendarDays,
  Check,
  ClipboardList,
  Code2,
  Copy,
  FileText,
  GraduationCap,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/design-system/cn";

import { IconButton } from "@/design-system/icon-button";
import { fadeRise } from "@/design-system/motion";
import { MarkdownContent } from "@/features/chat/components/markdown-content";
import { markdownToPlainText } from "@/features/chat/lib/normalize-markdown";
import {
  dedupeSources,
  documentKind,
  documentKindLabel,
  documentTitle,
  type DocumentKind,
} from "@/shared/lib/document-label";
import type { MessageDto, SourceReference, VerificationConfidence } from "@/shared/types/api";

/**
 * Un intercambio institucional se compone como una sección de documento: la
 * pregunta es el titular y la respuesta su cuerpo.
 *
 * Los turnos sociales son la excepción. Tratar «Hola» como encabezado de sección
 * producía un titular gigante seguido de vacío. Un saludo es conversación, no
 * documento, y se compone como tal: compacto y sin jerarquía de título.
 */
function QuestionBlockImpl({
  content,
  isFirst,
  compact,
}: {
  content: string;
  isFirst: boolean;
  compact: boolean;
}) {
  if (compact) {
    return (
      <motion.p
        variants={fadeRise}
        initial="hidden"
        animate="visible"
        className={cn("text-body text-muted-foreground font-medium", isFirst ? "" : "mt-10")}
      >
        {content}
      </motion.p>
    );
  }

  return (
    <motion.h2
      variants={fadeRise}
      initial="hidden"
      animate="visible"
      className={cn("text-title text-foreground text-balance", isFirst ? "" : "mt-16")}
    >
      {content}
    </motion.h2>
  );
}

export const QuestionBlock = memo(QuestionBlockImpl);

/**
 * Icono según el tipo de documento.
 *
 * El mismo icono repetido cinco veces convierte la lista en una textura que el
 * ojo deja de leer. Distinguir reglamento, calendario y plan de estudios permite
 * reconocer de qué clase de norma viene la respuesta antes de leer el título.
 */
const KIND_ICON: Record<DocumentKind, typeof FileText> = {
  reglamento: BookMarked,
  calendario: CalendarDays,
  proceso: ClipboardList,
  plan: GraduationCap,
  documento: FileText,
};

const CONFIDENCE_LABEL: Record<VerificationConfidence, string> = {
  high: "Confianza alta",
  medium: "Confianza media",
  low: "Cobertura parcial",
};

/**
 * Referencias documentales, no nombres de archivo.
 *
 * Se descartan duplicados —el corpus los tiene— y cada fuente se compone como
 * una tarjeta con su tipo de documento. El orden de llegada ya es el de
 * relevancia, porque el backend lista los documentos según el fragmento mejor
 * puntuado que los cita.
 *
 * La confianza se muestra **una vez**, sobre el conjunto, y no repetida en cada
 * tarjeta: el backend verifica la respuesta completa contra los documentos, no
 * documento a documento. Atribuir una confianza a cada fuente por separado sería
 * presentar como dato algo que el sistema no calcula.
 */
function SourceList({
  sources,
  confidence,
}: {
  sources: SourceReference[];
  confidence: VerificationConfidence | null;
}) {
  const unique = dedupeSources(sources);

  return (
    <section className="border-hairline mt-8 border-t pt-5" aria-label="Fuentes consultadas">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1.5">
        <h3 className="text-micro text-text-tertiary font-semibold uppercase">
          {unique.length === 1 ? "Fuente" : `Fuentes · ${unique.length}`}
        </h3>
        {confidence && (
          <span className="text-micro text-text-tertiary tracking-normal">
            {CONFIDENCE_LABEL[confidence]}
          </span>
        )}
      </div>

      {/* Tarjetas, no enlaces: abrir el documento todavía no existe, y un elemento
          con aspecto de enlace que no navega a ningún sitio es una promesa falsa.
          El cambio de superficie al pasar el cursor comunica «objeto», no «acción». */}
      <ul className="mt-3.5 grid gap-2 sm:grid-cols-2">
        {unique.map((source, index) => {
          const Icon = KIND_ICON[documentKind(source.document_name)];
          return (
            <li
              key={`${index}-${source.document_name}-${source.page_number ?? "n"}`}
              className="ring-hairline hover:bg-surface-raised-hover flex items-start gap-3 rounded-xl px-3 py-2.5 ring-1 transition-colors duration-200 ease-soft"
            >
              <span className="bg-muted text-muted-foreground mt-px flex size-7 shrink-0 items-center justify-center rounded-lg">
                <Icon className="size-3.5" strokeWidth={1.75} />
              </span>
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="text-caption text-foreground leading-snug font-medium">
                  {documentTitle(source.document_name)}
                </span>
                <span className="text-micro text-text-tertiary tracking-normal">
                  {documentKindLabel(source.document_name)}
                  {/* El número de página está modelado en el backend pero es
                      siempre nulo en este sprint: la ingesta todavía no lo
                      registra. Se dibuja sólo cuando llega de verdad. */}
                  {source.page_number != null && ` · pág. ${source.page_number}`}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** Señal de verificación como nota al pie, nunca como etiqueta de color. */
function GroundingNote({
  isGrounded,
  confidence,
}: {
  isGrounded: boolean;
  confidence: VerificationConfidence | null;
}) {
  const Icon = isGrounded ? ShieldCheck : ShieldAlert;

  const text = !isGrounded
    ? "No encontré normativa que respalde una respuesta a esto."
    : confidence === "low"
      ? "Verificado contra la normativa, aunque la cobertura es parcial."
      : confidence === "medium"
        ? "Verificado contra la normativa, con algunos matices."
        : "Verificado contra la normativa oficial.";

  return (
    <p className="text-caption text-muted-foreground mt-6 flex items-start gap-2">
      <Icon className="mt-[0.2em] size-3.5 shrink-0" strokeWidth={1.75} />
      {text}
    </p>
  );
}

function CopyButton({
  label,
  done,
  onCopy,
  children,
}: {
  label: string;
  done: boolean;
  onCopy: () => void;
  children: ReactNode;
}) {
  return (
    <IconButton size="sm" label={done ? "Copiado" : label} onClick={onCopy}>
      {done ? <Check className="text-primary size-4" strokeWidth={2.25} /> : children}
    </IconButton>
  );
}

/**
 * Copiar con dos destinos distintos.
 *
 * Una respuesta normativa se lleva a un correo o a un trabajo, donde `**` y `-`
 * son ruido; pero quien la pega en un documento en Markdown quiere justo lo
 * contrario. Son dos usos reales, así que son dos acciones y no un menú que las
 * esconda.
 */
function AnswerActions({ content }: { content: string }) {
  const [copied, setCopied] = useState<"text" | "markdown" | null>(null);

  const copy = async (text: string, kind: "text" | "markdown") => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 2000);
    } catch {
      // Sin permiso de portapapeles (contexto no seguro): el usuario todavía puede
      // seleccionar el texto a mano, así que no se le interrumpe con un error.
    }
  };

  return (
    // Visible siempre en táctil (donde no hay cursor que pasar por encima) y al
    // acercarse en escritorio. `focus-within` la mantiene al navegar con teclado.
    <div className="mt-4 flex items-center gap-1 transition-opacity duration-200 ease-soft sm:opacity-0 sm:group-focus-within/answer:opacity-100 sm:group-hover/answer:opacity-100">
      <CopyButton
        label="Copiar respuesta"
        done={copied === "text"}
        onCopy={() => void copy(markdownToPlainText(content), "text")}
      >
        <Copy className="size-4" strokeWidth={1.75} />
      </CopyButton>
      <CopyButton
        label="Copiar en Markdown"
        done={copied === "markdown"}
        onCopy={() => void copy(content, "markdown")}
      >
        <Code2 className="size-4" strokeWidth={1.75} />
      </CopyButton>
    </div>
  );
}

function AnswerBlockImpl({
  message,
  compact,
}: {
  message: Pick<MessageDto, "content" | "is_grounded" | "confidence" | "sources">;
  compact: boolean;
}) {
  const hasSources = message.sources.length > 0;

  return (
    <motion.div
      variants={fadeRise}
      initial="hidden"
      animate="visible"
      className={cn("group/answer", compact ? "mt-3" : "mt-7")}
    >
      <MarkdownContent content={message.content} />

      {hasSources && <SourceList sources={message.sources} confidence={message.confidence} />}
      {/* Con fuentes a la vista y confianza alta, repetir "verificado" es redundante:
          la propia lista ya lo indica. La nota reaparece cuando la cobertura es
          parcial, que es justo cuando el matiz importa. */}
      {message.is_grounded !== null &&
        !(message.is_grounded && hasSources && message.confidence === "high") && (
          <GroundingNote isGrounded={message.is_grounded} confidence={message.confidence} />
        )}

      {/* Un turno social no se copia ni se cita: no hay nada que llevarse. */}
      {!compact && <AnswerActions content={message.content} />}
    </motion.div>
  );
}

/**
 * Memoizado porque el hilo se vuelve a renderizar por motivos ajenos a él: el
 * sondeo de salud cada 30 segundos, el envío de una pregunta nueva, abrir el
 * panel lateral. Sin esto, cada uno de esos renders volvía a parsear el Markdown
 * de **todas** las respuestas del historial.
 */
export const AnswerBlock = memo(AnswerBlockImpl);
