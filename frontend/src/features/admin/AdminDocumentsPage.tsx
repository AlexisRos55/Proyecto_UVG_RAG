import { useRef } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useDeleteDocument,
  useDocuments,
  useReindexDocument,
  useUploadDocument,
} from "@/features/admin/api";
import { DocumentRow } from "@/features/admin/components/document-row";
import { ApiError } from "@/shared/lib/api-client";

export function AdminDocumentsPage() {
  const { data: documents, isLoading } = useDocuments();
  const uploadDocument = useUploadDocument();
  const deleteDocument = useDeleteDocument();
  const reindexDocument = useReindexDocument();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isBusy = uploadDocument.isPending || deleteDocument.isPending || reindexDocument.isPending;

  const handleFileSelected = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    uploadDocument.mutate(file, {
      onSuccess: (result) => {
        if (result.status === "error") {
          toast.error(`No se pudo indexar '${result.filename}': ${result.error_message}`);
        } else {
          toast.success(`'${result.filename}' indexado (${result.chunk_count} fragmentos).`);
        }
      },
      onError: (error: unknown) => {
        const message = error instanceof ApiError ? error.message : "No se pudo subir el documento.";
        toast.error(message);
      },
    });
    event.target.value = "";
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Panel administrativo de documentos</h1>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/chat">Volver al chat</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Subir un nuevo documento oficial (PDF)</CardTitle>
        </CardHeader>
        <CardContent>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileSelected}
          />
          <Button onClick={() => fileInputRef.current?.click()} disabled={uploadDocument.isPending}>
            {uploadDocument.isPending ? "Subiendo e indexando..." : "Seleccionar PDF"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Documentos administrados</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-sm text-muted-foreground">Cargando…</p>}
          {!isLoading && documents?.length === 0 && (
            <p className="text-sm text-muted-foreground">Todavía no hay documentos indexados.</p>
          )}
          {documents?.map((document) => (
            <DocumentRow
              key={document.document_id}
              document={document}
              isBusy={isBusy}
              onReindex={(id) =>
                reindexDocument.mutate(id, {
                  onError: () => toast.error("No se pudo reindexar el documento."),
                  onSuccess: () => toast.success("Documento reindexado."),
                })
              }
              onDelete={(id) =>
                deleteDocument.mutate(id, {
                  onError: () => toast.error("No se pudo eliminar el documento."),
                  onSuccess: () => toast.success("Documento eliminado."),
                })
              }
            />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
