import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Clock, FileText, RotateCw, Trash2 } from "lucide-react";
import { cn } from "@/design-system/cn";

import { IconButton } from "@/design-system/icon-button";
import { transition } from "@/design-system/motion";
import { documentDisplayName } from "@/shared/lib/document-name";
import type { DocumentStatus, DocumentSummary } from "@/shared/types/api";

const STATUS: Record<
  DocumentStatus,
  { label: string; className: string; icon: typeof CheckCircle2 }
> = {
  indexed: {
    label: "Indexado",
    className: "text-primary bg-primary/10",
    icon: CheckCircle2,
  },
  pending: {
    label: "Pendiente",
    className: "text-muted-foreground bg-muted",
    icon: Clock,
  },
  error: {
    label: "Con error",
    className: "text-destructive bg-destructive/10",
    icon: AlertCircle,
  },
};

interface DocumentRowProps {
  document: DocumentSummary;
  /** Solo esta fila está ocupada: antes cualquier acción congelaba la lista entera. */
  isPending: boolean;
  /** Cualquier otra fila está trabajando; se evita lanzar acciones en paralelo. */
  isDisabled: boolean;
  onReindex: (id: string) => void;
  onDelete: (document: DocumentSummary) => void;
}

export function DocumentRow({
  document,
  isPending,
  isDisabled,
  onReindex,
  onDelete,
}: DocumentRowProps) {
  const status = STATUS[document.status];
  const StatusIcon = status.icon;
  const name = documentDisplayName(document.filename);

  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={transition.base}
      className={cn(
        "group hover:bg-muted/60 flex items-center gap-3 rounded-xl px-3 py-3 transition-colors",
        isPending && "opacity-60",
      )}
    >
      <span className="bg-muted text-muted-foreground flex size-9 shrink-0 items-center justify-center rounded-lg">
        <FileText className="size-4" strokeWidth={1.75} />
      </span>

      <div className="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
        <p className="text-ui text-foreground min-w-0 truncate" title={name}>
          {name}
        </p>
        <span
          className={cn(
            "text-micro inline-flex w-fit shrink-0 items-center gap-1 rounded-full px-2 py-0.5 font-medium tracking-normal",
            status.className,
          )}
        >
          <StatusIcon className="size-3" strokeWidth={2} />
          {status.label}
        </span>
        {document.error_message && (
          <span className="text-caption text-destructive min-w-0 break-words">
            {document.error_message}
          </span>
        )}
      </div>

      {/* Presentes siempre —esta es una pantalla de gestión, esconder las acciones
          tras el cursor las haría indescubribles— pero atenuadas hasta que la fila
          recibe atención, para que la lista se lea sin ruido de controles. */}
      <div className="flex shrink-0 items-center gap-1 opacity-70 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
        <IconButton
          size="sm"
          label={`Reindexar ${name}`}
          disabled={isDisabled}
          onClick={() => onReindex(document.document_id)}
        >
          <RotateCw className={cn("size-4", isPending && "animate-spin")} strokeWidth={1.75} />
        </IconButton>
        <IconButton
          size="sm"
          label={`Eliminar ${name}`}
          disabled={isDisabled}
          onClick={() => onDelete(document)}
          className="hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="size-4" strokeWidth={1.75} />
        </IconButton>
      </div>
    </motion.li>
  );
}
