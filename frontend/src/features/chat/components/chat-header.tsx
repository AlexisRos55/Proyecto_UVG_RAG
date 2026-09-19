import { Menu } from "lucide-react";
import { cn } from "@/design-system/cn";

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
        <p className="text-ui text-muted-foreground hidden min-w-0 flex-1 truncate lg:block">
          {title}
        </p>
      )}

      {/* El estado se anuncia siempre, aunque la etiqueta visible se oculte en
          pantallas estrechas: antes el punto era `aria-hidden` y el texto
          `hidden sm:inline`, así que en móvil la caída del servidor no llegaba
          ni a la vista ni al lector de pantalla. */}
      <p className="ml-auto flex items-center gap-2" role="status">
        <span className="sr-only">
          {isOnline ? "Conectado con el servidor" : "Sin conexión con el servidor"}
        </span>
        {/* Punto sólido, sin pulso permanente: una animación infinita mantiene una
            capa de composición activa toda la sesión y, sobre todo, «en línea» no
            es una novedad que haya que seguir anunciando. */}
        <span
          className={cn(
            "size-1.5 shrink-0 rounded-full transition-colors duration-300",
            isOnline ? "bg-primary" : "bg-destructive",
          )}
          aria-hidden="true"
        />
        <span className="text-caption text-muted-foreground hidden sm:inline" aria-hidden="true">
          {isOnline ? "En línea" : "Sin conexión"}
        </span>
      </p>
    </header>
  );
}
