import type { ReactNode } from "react";
import { AlertDialog } from "radix-ui";
import { cn } from "@/design-system/cn";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  /** Marca la acción como irreversible: tratamiento visual de destrucción. */
  destructive?: boolean;
  isPending?: boolean;
  onConfirm: () => void;
}

/**
 * Fricción proporcional al daño.
 *
 * Toda acción irreversible pasa por aquí. La confirmación nombra explícitamente
 * lo que se va a destruir —para que el usuario lea qué está a punto de perder— y
 * la acción destructiva se separa visualmente de la segura, que además es la que
 * recibe el foco inicial.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel = "Cancelar",
  destructive = false,
  isPending = false,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px]" />
        <AlertDialog.Content
          className={cn(
            "bg-popover shadow-float fixed top-1/2 left-1/2 z-50 w-[calc(100vw-2rem)] max-w-[26rem]",
            "-translate-x-1/2 -translate-y-1/2 rounded-2xl p-6",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
            "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          )}
        >
          <AlertDialog.Title className="text-heading text-foreground">{title}</AlertDialog.Title>
          <AlertDialog.Description className="text-ui text-muted-foreground mt-2.5">
            {description}
          </AlertDialog.Description>

          <div className="mt-7 flex flex-col-reverse gap-2.5 sm:flex-row sm:justify-end">
            <AlertDialog.Cancel
              className={cn(
                "text-ui ring-border hover:bg-muted rounded-xl px-4 py-2.5 font-medium ring-1",
                "focus-visible:ring-ring transition-colors focus-visible:ring-2 focus-visible:outline-none",
              )}
            >
              {cancelLabel}
            </AlertDialog.Cancel>
            <AlertDialog.Action
              onClick={(event) => {
                // Se cierra desde el estado del llamador, no al hacer clic: así el
                // diálogo puede mostrar el progreso de la acción.
                event.preventDefault();
                onConfirm();
              }}
              disabled={isPending}
              className={cn(
                "text-ui rounded-xl px-4 py-2.5 font-medium transition-colors",
                "focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none",
                "disabled:cursor-not-allowed disabled:opacity-60",
                destructive
                  ? "bg-destructive text-destructive-foreground hover:opacity-90"
                  : "bg-primary text-primary-foreground hover:opacity-90",
              )}
            >
              {isPending ? "Eliminando…" : confirmLabel}
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
