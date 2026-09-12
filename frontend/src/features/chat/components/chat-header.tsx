import { Menu } from "lucide-react";

import { BrandLockup } from "@/design-system/brand";
import { IconButton } from "@/design-system/icon-button";

interface ChatHeaderProps {
  title: string | null;
  isOnline: boolean;
  onOpenSidebar: () => void;
}

/**
 * Cabecera flotante y translúcida: el contenido pasa por debajo al hacer scroll,
 * como en una aplicación nativa. No lleva borde inferior ni etiqueta de modelo
 * -- en escritorio queda prácticamente vacía para que el protagonista sea la
 * conversación. La marca sólo aparece en móvil, donde el sidebar está oculto.
 */
export function ChatHeader({ title, isOnline, onOpenSidebar }: ChatHeaderProps) {
  return (
    <header className="bg-background/70 pointer-events-none absolute inset-x-0 top-0 z-20 flex h-[var(--header-height)] items-center gap-3 px-4 backdrop-blur-xl sm:px-6">
      <div className="pointer-events-auto flex items-center gap-2.5 lg:hidden">
        <IconButton label="Abrir menú" onClick={onOpenSidebar}>
          <Menu className="size-5" strokeWidth={1.75} />
        </IconButton>
        <BrandLockup compact />
      </div>

      {title && (
        <p className="text-ui text-muted-foreground/80 hidden min-w-0 flex-1 truncate lg:block">
          {title}
        </p>
      )}

      <div className="ml-auto flex items-center gap-2">
        {/* El punto de estado usa el verde institucional, no un verde genérico de
            paleta: es el detalle de color más repetido de la interfaz. */}
        <span className="relative flex size-1.5 shrink-0" aria-hidden="true">
          {isOnline && (
            <span className="bg-primary/40 absolute inline-flex size-full animate-ping rounded-full" />
          )}
          <span
            className={`relative inline-flex size-1.5 rounded-full ${isOnline ? "bg-primary" : "bg-destructive"}`}
          />
        </span>
        <span className="text-caption text-muted-foreground/70 hidden sm:inline">
          {isOnline ? "En línea" : "Sin conexión"}
        </span>
      </div>
    </header>
  );
}
