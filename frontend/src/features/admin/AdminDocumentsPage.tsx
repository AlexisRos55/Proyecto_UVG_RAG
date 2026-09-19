import { useMemo, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, FileUp, LoaderCircle, Search, Upload } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/design-system/cn";

import { BrandLockup } from "@/design-system/brand";
import { ConfirmDialog } from "@/design-system/confirm-dialog";
import { IconButton } from "@/design-system/icon-button";
import { transition } from "@/design-system/motion";
import { EmptyState, ErrorState, LoadingState } from "@/design-system/states";
import {
  useDeleteDocument,
  useDocuments,
  useReindexDocument,
  useUploadDocument,
} from "@/features/admin/api";
import { DocumentRow } from "@/features/admin/components/document-row";
import { ThemeToggle } from "@/features/chat/components/theme-toggle";
import { ApiError } from "@/shared/lib/api-client";
import { documentDisplayName } from "@/shared/lib/document-name";
import type { DocumentSummary } from "@/shared/types/api";

const MAX_UPLOAD_MB = 25;

export function AdminDocumentsPage() {
  const { data: documents, isLoading, isError, error, refetch, isFetching } = useDocuments();
  const uploadDocument = useUploadDocument();
  const deleteDocument = useDeleteDocument();
  const reindexDocument = useReindexDocument();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<DocumentSummary | null>(null);
  const [activeRowId, setActiveRowId] = useState<string | null>(null);

  const isMutating = uploadDocument.isPending || deleteDocument.isPending || reindexDocument.isPending;

  const visibleDocuments = useMemo(() => {
    const list = documents ?? [];
    const term = query.trim().toLowerCase();
    if (!term) return list;
    return list.filter((document) =>
      documentDisplayName(document.filename).toLowerCase().includes(term),
    );
  }, [documents, query]);

  const upload = (file: File) => {
    if (file.type !== "application/pdf") {
      toast.error("Solo se admiten documentos PDF.");
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      toast.error(`El archivo supera el límite de ${MAX_UPLOAD_MB} MB.`);
      return;
    }

    uploadDocument.mutate(file, {
      onSuccess: (result) => {
        const name = documentDisplayName(result.filename);
        if (result.status === "error") {
          toast.error(`No se pudo indexar «${name}»`, { description: result.error_message ?? undefined });
        } else {
          toast.success(`«${name}» quedó indexado`, {
            description: `${result.chunk_count} fragmentos disponibles para consulta.`,
          });
        }
      },
      onError: (mutationError: unknown) => {
        toast.error(
          mutationError instanceof ApiError
            ? mutationError.message
            : "No se pudo subir el documento.",
        );
      },
    });
  };

  const handleFileSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) upload(file);
    event.target.value = "";
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDraggingOver(false);
    const file = event.dataTransfer.files?.[0];
    if (file) upload(file);
  };

  const handleReindex = (id: string) => {
    setActiveRowId(id);
    reindexDocument.mutate(id, {
      onSuccess: () => toast.success("Documento reindexado."),
      onError: () => toast.error("No se pudo reindexar el documento."),
      onSettled: () => setActiveRowId(null),
    });
  };

  const confirmDelete = () => {
    if (!pendingDelete) return;
    const name = documentDisplayName(pendingDelete.filename);
    setActiveRowId(pendingDelete.document_id);
    deleteDocument.mutate(pendingDelete.document_id, {
      onSuccess: () => toast.success(`«${name}» fue eliminado del corpus.`),
      onError: () => toast.error("No se pudo eliminar el documento."),
      onSettled: () => {
        setActiveRowId(null);
        setPendingDelete(null);
      },
    });
  };

  return (
    <div className="bg-background flex min-h-svh flex-col">
      <header className="border-hairline flex h-14 shrink-0 items-center gap-3 border-b px-4 sm:px-8">
        <IconButton label="Volver al asistente" asChild>
          <Link to="/chat">
            <ArrowLeft className="size-5" strokeWidth={1.75} />
          </Link>
        </IconButton>
        <BrandLockup compact />
        <span className="text-ui text-muted-foreground ml-1 hidden sm:inline">
          · Documentos oficiales
        </span>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 py-10 sm:px-8">
        <h1 className="text-display text-foreground">Documentos</h1>
        <p className="text-body text-muted-foreground mt-3 max-w-xl">
          El asistente responde únicamente con base en los documentos indexados aquí. Cada archivo
          que agregues queda disponible de inmediato para las consultas de los estudiantes.
        </p>

        {/* Zona de carga: admite arrastrar y soltar, con validación previa de tipo
            y tamaño para no gastar una subida larga en un archivo inválido. */}
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setIsDraggingOver(true);
          }}
          onDragLeave={() => setIsDraggingOver(false)}
          onDrop={handleDrop}
          className={cn(
            "mt-8 flex flex-col items-center gap-3 rounded-2xl border border-dashed px-6 py-10 text-center transition-colors",
            isDraggingOver ? "border-primary bg-primary/[0.04]" : "border-border",
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="sr-only"
            onChange={handleFileSelected}
            aria-label="Seleccionar documento PDF"
          />

          <span className="bg-muted text-muted-foreground flex size-11 items-center justify-center rounded-full">
            {uploadDocument.isPending ? (
              <LoaderCircle className="size-5 animate-spin" strokeWidth={1.75} />
            ) : (
              <FileUp className="size-5" strokeWidth={1.75} />
            )}
          </span>

          {uploadDocument.isPending ? (
            <div className="flex flex-col gap-1">
              <p className="text-ui text-foreground font-medium">Indexando documento…</p>
              <p className="text-caption text-muted-foreground">
                Extrayendo texto y generando fragmentos. Puede tardar un momento.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              <p className="text-ui text-foreground font-medium">
                Arrastra un PDF o selecciónalo desde tu equipo
              </p>
              <p className="text-caption text-muted-foreground">
                Solo PDF, hasta {MAX_UPLOAD_MB} MB.
              </p>
            </div>
          )}

          <motion.button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadDocument.isPending}
            whileTap={{ scale: 0.98 }}
            transition={transition.spring}
            className={cn(
              "text-ui bg-primary text-primary-foreground mt-1 inline-flex items-center gap-2 rounded-xl px-4 py-2.5 font-medium",
              "transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60",
              "focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none",
            )}
          >
            <Upload className="size-4" strokeWidth={2} />
            Seleccionar PDF
          </motion.button>
        </div>

        <section className="mt-12">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-heading text-foreground">
              Indexados
              {documents && documents.length > 0 && (
                <span className="text-muted-foreground ml-2 font-normal">{documents.length}</span>
              )}
            </h2>

            {documents && documents.length > 4 && (
              <div className="relative">
                <Search
                  className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
                  strokeWidth={1.75}
                  aria-hidden="true"
                />
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar documento"
                  aria-label="Buscar documento"
                  className={cn(
                    "text-ui bg-card border-input text-foreground placeholder:text-muted-foreground h-9 w-56 rounded-xl border pr-3 pl-9",
                    "focus-visible:border-primary focus-visible:ring-primary/25 focus-visible:ring-2 focus-visible:outline-none",
                  )}
                />
              </div>
            )}
          </div>

          <div className="mt-4">
            {isLoading ? (
              <LoadingState label="Cargando documentos" rows={4} />
            ) : isError ? (
              /* Antes esta rama no existía: un fallo dejaba la tarjeta vacía y el
                 administrador leía "no hay documentos" donde había un error. */
              <ErrorState error={error} onRetry={() => void refetch()} />
            ) : visibleDocuments.length === 0 ? (
              query ? (
                <EmptyState
                  icon={Search}
                  compact
                  title="Sin coincidencias"
                  description={`Ningún documento indexado coincide con «${query}».`}
                />
              ) : (
                <EmptyState
                  icon={FileUp}
                  title="Todavía no hay documentos"
                  description="Sube el primer reglamento o normativa oficial para que el asistente pueda responder consultas."
                />
              )
            ) : (
              <ul className="flex flex-col">
                <AnimatePresence initial={false}>
                  {visibleDocuments.map((document) => (
                    <DocumentRow
                      key={document.document_id}
                      document={document}
                      isPending={activeRowId === document.document_id}
                      isDisabled={isMutating && activeRowId !== document.document_id}
                      onReindex={handleReindex}
                      onDelete={setPendingDelete}
                    />
                  ))}
                </AnimatePresence>
              </ul>
            )}

            {isFetching && !isLoading && (
              <p className="text-caption text-muted-foreground mt-3" role="status">
                Actualizando…
              </p>
            )}
          </div>
        </section>
      </main>

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        destructive
        isPending={deleteDocument.isPending}
        title="¿Eliminar este documento?"
        description={
          <>
            <span className="text-foreground font-medium">
              {pendingDelete ? documentDisplayName(pendingDelete.filename) : ""}
            </span>{" "}
            dejará de estar indexado y el asistente no podrá volver a citarlo. Esta acción no se
            puede deshacer.
          </>
        }
        confirmLabel="Eliminar documento"
        onConfirm={confirmDelete}
      />
    </div>
  );
}
