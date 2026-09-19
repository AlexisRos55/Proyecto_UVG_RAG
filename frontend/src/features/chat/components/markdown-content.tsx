import { memo, useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/design-system/cn";

import { normalizeMarkdown } from "@/features/chat/lib/normalize-markdown";

/**
 * Tipografía de documento, no de chat.
 *
 * El ritmo vertical es deliberadamente amplio porque las respuestas son texto
 * normativo que se lee, no mensajes que se ojean. No se añade resaltado de
 * sintaxis: el dominio es reglamentario, no técnico.
 *
 * La cobertura es completa a propósito —encabezados, listas de ambos tipos,
 * tablas, citas, código, enlaces, separadores y tachado— para que ningún
 * elemento que el modelo pueda emitir caiga en el estilo por defecto del
 * navegador y rompa la consistencia visual.
 */
const markdownComponents: Components = {
  // `text-wrap: pretty` evita la línea final de una sola palabra, que en textos
  // largos aparece constantemente y es la diferencia entre un párrafo compuesto
  // y un párrafo volcado.
  p: ({ children }) => (
    <p className="[&:not(:first-child)]:mt-5 [text-wrap:pretty]">{children}</p>
  ),

  // El turno del estudiante ya encabeza la sección: los encabezados del modelo
  // bajan un nivel para no competir con él.
  h1: ({ children }) => (
    <h3 className="text-heading mt-9 mb-3 text-balance first:mt-0">{children}</h3>
  ),
  h2: ({ children }) => (
    <h3 className="text-heading mt-9 mb-3 text-balance first:mt-0">{children}</h3>
  ),
  h3: ({ children }) => (
    <h4 className="text-ui mt-7 mb-2 font-semibold text-balance first:mt-0">{children}</h4>
  ),
  h4: ({ children }) => (
    <h5 className="text-ui text-muted-foreground mt-6 mb-2 font-semibold first:mt-0">{children}</h5>
  ),
  h5: ({ children }) => (
    <h6 className="text-caption text-muted-foreground mt-5 mb-1.5 font-semibold tracking-wide uppercase first:mt-0">
      {children}
    </h6>
  ),
  h6: ({ children }) => (
    <h6 className="text-caption text-muted-foreground mt-5 mb-1.5 font-semibold tracking-wide uppercase first:mt-0">
      {children}
    </h6>
  ),

  // Viñeta dibujada a mano: un punto pequeño y tenue pesa mucho menos que el
  // marcador del navegador. Se aplica desde el <ul> con un selector de hijo
  // porque react-markdown v10 ya no informa al <li> si su lista es ordenada.
  ul: ({ children }) => (
    <ul className="my-4 space-y-2.5 [&>li]:relative [&>li]:pl-5 [&>li]:before:absolute [&>li]:before:top-[0.72em] [&>li]:before:left-[0.3rem] [&>li]:before:size-[3px] [&>li]:before:rounded-full [&>li]:before:bg-current [&>li]:before:opacity-35 [&_ul]:mt-2.5 [&_ul]:mb-0">
      {children}
    </ul>
  ),
  // Los pasos numerados son el formato de cualquier trámite («¿cómo solicito
  // una beca?»). `tabular-nums` alinea el 9 con el 10 en listas largas, donde
  // sin ello el texto de cada paso empieza en una columna distinta.
  ol: ({ children }) => (
    <ol className="marker:text-muted-foreground my-4 list-decimal space-y-2.5 pl-6 marker:font-semibold marker:tabular-nums [&>li]:pl-1 [&_ol]:mt-2.5 [&_ol]:mb-0">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="[text-wrap:pretty] [&>p]:m-0 [&>p:not(:first-child)]:mt-2">{children}</li>
  ),

  strong: ({ children }) => <strong className="text-foreground font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  del: ({ children }) => <del className="text-muted-foreground line-through">{children}</del>,

  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-primary decoration-primary/30 hover:decoration-primary focus-visible:ring-ring rounded-sm font-medium underline underline-offset-[3px] transition-colors focus-visible:ring-2 focus-visible:outline-none"
    >
      {children}
    </a>
  ),

  // En este dominio una cita es casi siempre el texto literal de un artículo del
  // reglamento. Se compone como tal: superficie propia, para que se distinga del
  // resumen del asistente y se vea qué palabras son de la norma.
  blockquote: ({ children }) => (
    <blockquote className="border-primary/35 bg-foreground/[0.025] text-muted-foreground my-5 rounded-r-lg border-l-2 py-3 pr-4 pl-4 [&>p]:my-0 [&>p:not(:first-child)]:mt-3">
      {children}
    </blockquote>
  ),

  hr: () => <hr className="border-hairline my-8" />,

  code: ({ className, children, ...props }) => {
    const isBlock = /language-/.test(className ?? "");
    if (isBlock) {
      return (
        <code className="font-mono text-[0.875rem] leading-relaxed" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="bg-foreground/[0.05] rounded-md px-1.5 py-0.5 font-mono text-[0.875em]"
        {...props}
      >
        {children}
      </code>
    );
  },

  pre: ({ children }) => (
    <pre className="bg-foreground/[0.04] my-5 overflow-x-auto rounded-xl p-4">{children}</pre>
  ),

  // Las tablas son el formato estrella para comparaciones. Llevan su propio
  // contenedor con desplazamiento para que en móvil no empujen la página.
  table: ({ children }) => (
    <div className="border-hairline my-6 overflow-x-auto rounded-xl border">
      <table className="text-ui w-full border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-foreground/[0.03]">{children}</thead>,
  // Resaltar la fila bajo el cursor es lo que permite seguir una comparación de
  // varias columnas sin perder el renglón.
  tr: ({ children }) => (
    <tr className="hover:bg-foreground/[0.02] transition-colors duration-150 ease-soft">
      {children}
    </tr>
  ),
  th: ({ children }) => (
    <th className="border-hairline text-muted-foreground border-b px-3.5 py-2.5 text-left font-semibold whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-hairline border-b px-3.5 py-2.5 align-top tabular-nums [tr:last-child>&]:border-b-0">
      {children}
    </td>
  ),
};

function MarkdownContentImpl({ content, className }: { content: string; className?: string }) {
  // El prompt pide Markdown válido, pero un modelo no es un contrato: se
  // normaliza antes de renderizar para que una viñeta literal no degrade la
  // presentación (ver normalize-markdown.ts).
  const normalized = useMemo(() => normalizeMarkdown(content), [content]);

  return (
    // `break-words` evita que un código institucional largo o una URL sin
    // espacios desborde la columna de lectura en móvil.
    <div className={cn("text-body text-foreground break-words", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {normalized}
      </ReactMarkdown>
    </div>
  );
}

/** El parseo de Markdown es el trabajo más caro del hilo: no se repite si el
 *  texto no cambió (ver la nota de memoización en `message-turn.tsx`). */
export const MarkdownContent = memo(MarkdownContentImpl);
