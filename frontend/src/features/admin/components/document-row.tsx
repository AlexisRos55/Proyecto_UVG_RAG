import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DocumentSummary } from "@/shared/types/api";

const STATUS_VARIANT: Record<DocumentSummary["status"], "secondary" | "destructive" | "outline"> = {
  indexed: "secondary",
  error: "destructive",
  pending: "outline",
};

const STATUS_LABEL: Record<DocumentSummary["status"], string> = {
  indexed: "Indexado",
  error: "Error",
  pending: "Pendiente",
};

interface DocumentRowProps {
  document: DocumentSummary;
  onReindex: (id: string) => void;
  onDelete: (id: string) => void;
  isBusy: boolean;
}

export function DocumentRow({ document, onReindex, onDelete, isBusy }: DocumentRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 border-b py-3 last:border-b-0">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{document.filename}</p>
        {document.error_message && (
          <p className="truncate text-xs text-destructive">{document.error_message}</p>
        )}
      </div>
      <Badge variant={STATUS_VARIANT[document.status]}>{STATUS_LABEL[document.status]}</Badge>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={isBusy}
          onClick={() => onReindex(document.document_id)}
        >
          Reindexar
        </Button>
        <Button
          variant="destructive"
          size="sm"
          disabled={isBusy}
          onClick={() => onDelete(document.document_id)}
        >
          Eliminar
        </Button>
      </div>
    </div>
  );
}
