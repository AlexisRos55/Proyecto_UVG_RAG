import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "cn";

/**
 * Tipografía de documento, no de chat.
 *
 * El ritmo vertical es deliberadamente amplio (párrafos separados por 1.25rem,
 * títulos por más del doble) porque las respuestas son texto normativo que se
 * lee, no mensajes que se ojean. No se añade resaltado de sintaxis: el dominio
 * es reglamentario, no técnico, y una librería de highlighting no aportaría.
 */
const markdownComponents: Components = {
  p: ({ children }) => <p className="[&:not(:first-child)]:mt-5">{children}</p>,

  h1: ({ children }) => (
    <h2 className="text-heading mt-9 mb-3 first:mt-0">{children}</h2>
  ),
  h2: ({ children }) => (
    <h3 className="text-heading mt-9 mb-3 first:mt-0">{children}</h3>
  ),
  h3: ({ children }) => (
    <h4 className="text-ui mt-7 mb-2 font-semibold first:mt-0">{children}</h4>
  ),

  // Viñeta dibujada a mano (un punto pequeño y tenue pesa mucho menos que el
  // marcador del navegador). Se aplica desde el <ul> con un selector de hijo
  // porque react-markdown v10 ya no informa al <li> si su lista es ordenada.
  ul: ({ children }) => (
    <ul className="my-4 space-y-2.5 [&>li]:relative [&>li]:pl-5 [&>li]:before:absolute [&>li]:before:top-[0.72em] [&>li]:before:left-[0.3rem] [&>li]:before:size-[3px] [&>li]:before:rounded-full [&>li]:before:bg-current [&>li]:before:opacity-35">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="marker:text-muted-foreground my-4 list-decimal space-y-2.5 pl-5 [&>li]:pl-1">
      {children}
    </ol>
  ),

  strong: ({ children }) => <strong className="text-foreground font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,

  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-primary decoration-primary/30 hover:decoration-primary font-medium underline underline-offset-[3px] transition-colors"
    >
      {children}
    </a>
  ),

  blockquote: ({ children }) => (
    <blockquote className="border-primary/25 text-muted-foreground my-5 border-l-2 pl-4">
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

  table: ({ children }) => (
    <div className="my-6 overflow-x-auto">
      <table className="text-ui w-full border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-hairline text-muted-foreground border-b px-3 py-2.5 text-left font-semibold">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-hairline border-b px-3 py-2.5 align-top last:border-b-0">{children}</td>
  ),
};

export function MarkdownContent({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn("text-body text-foreground/85", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
