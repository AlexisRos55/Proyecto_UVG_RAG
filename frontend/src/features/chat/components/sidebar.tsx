import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";
import { FolderCog, LogOut, MessageSquare, Plus, X } from "lucide-react";
import { cn } from "@/design-system/cn";

import { BrandLockup } from "@/design-system/brand";
import { IconButton } from "@/design-system/icon-button";
import { EASE_STANDARD, transition } from "@/design-system/motion";
import { ThemeToggle } from "@/features/chat/components/theme-toggle";
import { groupByDate } from "@/features/chat/lib/conversation-groups";
import { formatRelativeDate } from "@/features/chat/lib/format";
import { useFocusTrap } from "@/shared/hooks/use-focus-trap";

export interface ConversationListItem {
  id: string;
  title: string;
  updatedAt: string;
}

interface SidebarProps {
  userEmail: string;
  /** Muestra el acceso a la gestión documental. Antes esa sección solo era
   *  alcanzable tecleando la URL: existía pero nadie podía descubrirla. */
  isAdmin: boolean;
  conversations: ConversationListItem[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onLogout: () => void;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * La lista itera sobre un arreglo aunque hoy el backend sólo sostenga un hilo
 * activo por estudiante (FR-14): cuando exista historial múltiple, esta vista
 * no cambia. Lo que NO se dibuja es el menú contextual de renombrar/eliminar/
 * fijar: no hay endpoints detrás y dibujarlo sería prometer una función
 * inexistente.
 */
function ConversationRow({
  conversation,
  isActive,
  onSelect,
}: {
  conversation: ConversationListItem;
  isActive: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      // `aria-current` es lo que informa al lector de pantalla de cuál es la
      // conversación abierta: la barra verde sólo lo dice a quien la ve.
      aria-current={isActive ? "true" : undefined}
      className={cn(
        "group relative flex w-full items-center gap-2.5 rounded-lg py-2 pr-2.5 pl-3 text-left",
        "transition-colors duration-200 ease-soft",
        "focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none",
        isActive ? "bg-foreground/[0.055]" : "hover:bg-foreground/[0.035]",
      )}
    >
      {/* Indicador activo: una barra verde de 2px que crece desde el centro. El
          único elemento del panel que usa color de marca de forma sostenida. */}
      <span
        className={cn(
          "bg-primary absolute top-1/2 left-0 w-0.5 -translate-y-1/2 rounded-full",
          "transition-all duration-300 ease-standard",
          isActive ? "h-4 opacity-100" : "h-0 opacity-0",
        )}
        aria-hidden="true"
      />
      <MessageSquare
        className={cn(
          "size-3.5 shrink-0 transition-colors duration-200",
          isActive ? "text-primary" : "text-text-tertiary group-hover:text-muted-foreground",
        )}
        strokeWidth={1.75}
      />
      <span className="flex min-w-0 flex-1 flex-col">
        <span
          className={cn(
            "text-ui truncate transition-colors duration-200",
            isActive ? "text-foreground" : "text-muted-foreground group-hover:text-foreground",
          )}
        >
          {conversation.title}
        </span>
        {/* Sobre la fila activa el token terciario cae a 4.32:1 —el velo del
            estado activo oscurece el fondo— y AA exige 4.5. Ahí sube un nivel;
            la jerarquía se sostiene igual porque el título pasa a `foreground`. */}
        <span
          className={cn(
            "text-micro tracking-normal",
            isActive ? "text-muted-foreground" : "text-text-tertiary",
          )}
        >
          {formatRelativeDate(conversation.updatedAt)}
        </span>
      </span>
    </button>
  );
}

function SidebarContent({
  userEmail,
  isAdmin,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onLogout,
  onCloseMobile,
}: Omit<SidebarProps, "isOpen" | "onClose"> & { onCloseMobile: () => void }) {
  // Los tramos («Hoy», «Esta semana»…) sustituyen al rótulo fijo «Reciente»:
  // ahora el encabezado dice algo verdadero sobre lo que hay debajo.
  const groups = useMemo(() => groupByDate(conversations), [conversations]);

  return (
    <div className="bg-sidebar relative flex h-full flex-col">
      {/* Firma institucional del panel: un velo verde de opacidad mínima que cae desde
          el logotipo y se desvanece, y una línea vertical de 1px en el borde derecho.
          Ambos casi imperceptibles -- marcan pertenencia, no decoran. */}
      <div
        className="from-primary/[0.028] pointer-events-none absolute inset-x-0 top-0 h-64 bg-gradient-to-b via-transparent to-transparent"
        aria-hidden="true"
      />
      <div
        className="via-primary/25 pointer-events-none absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent to-transparent"
        aria-hidden="true"
      />

      <div className="relative flex items-start justify-between gap-2 px-4 pt-5 pb-1">
        <BrandLockup />
        <IconButton label="Cerrar menú" onClick={onCloseMobile} size="sm" className="lg:hidden">
          <X className="size-4" />
        </IconButton>
      </div>

      <div className="relative px-3 pt-6">
        <motion.button
          type="button"
          onClick={onNewChat}
          whileTap={{ scale: 0.985 }}
          transition={transition.spring}
          className={cn(
            "text-ui bg-surface-raised group flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 font-medium",
            "shadow-soft hover:bg-surface-raised-hover transition-all duration-200 ease-standard",
            // Glow verde al pasar el cursor: la elevación se tiñe de marca en vez de
            // limitarse a oscurecerse.
            "hover:shadow-[0_4px_16px_-4px_color-mix(in_oklab,var(--primary)_28%,transparent)]",
            "focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none",
          )}
        >
          <Plus
            className="text-primary size-4 transition-transform duration-300 ease-standard group-hover:rotate-90"
            strokeWidth={2.25}
          />
          Nueva conversación
        </motion.button>
      </div>

      <nav
        className="relative min-h-0 flex-1 overflow-y-auto px-3 pt-6"
        aria-label="Conversaciones"
      >
        {groups.length === 0 ? (
          <>
            <p className="text-micro text-text-tertiary px-2.5 pb-2 font-semibold uppercase">
              Conversaciones
            </p>
            <p className="text-caption text-text-tertiary px-2.5">
              Tus conversaciones aparecerán aquí.
            </p>
          </>
        ) : (
          groups.map((group, index) => (
            <div key={group.bucket} className={index === 0 ? "" : "mt-5"}>
              <h2 className="text-micro text-text-tertiary px-2.5 pb-2 font-semibold uppercase">
                {group.label}
              </h2>
              <ul className="flex flex-col gap-0.5">
                {group.items.map((conversation) => (
                  <li key={conversation.id}>
                    <ConversationRow
                      conversation={conversation}
                      isActive={conversation.id === activeConversationId}
                      onSelect={() => onSelectConversation(conversation.id)}
                    />
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </nav>

      {isAdmin && (
        <div className="relative px-3 pb-1">
          <Link
            to="/admin"
            onClick={onCloseMobile}
            className={cn(
              "text-ui text-muted-foreground hover:text-foreground flex w-full items-center gap-2.5 rounded-lg px-3 py-2",
              "hover:bg-foreground/[0.035] transition-colors duration-200 ease-soft",
              "focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none",
            )}
          >
            <FolderCog className="size-4 shrink-0" strokeWidth={1.75} />
            Documentos oficiales
          </Link>
        </div>
      )}

      {/* Sin línea divisoria: la separación la da el espacio, no un borde. */}
      <div className="relative flex items-center gap-1 px-3 pt-3 pb-4">
        <div className="flex min-w-0 flex-1 items-center gap-2.5 px-1.5">
          <span className="bg-primary/12 text-primary text-micro ring-primary/15 flex size-7 shrink-0 items-center justify-center rounded-full font-semibold tracking-normal ring-1">
            {userEmail.charAt(0).toUpperCase()}
          </span>
          <span className="text-caption text-muted-foreground truncate" title={userEmail}>
            {userEmail}
          </span>
        </div>
        <ThemeToggle />
        <IconButton label="Cerrar sesión" size="sm" onClick={onLogout}>
          <LogOut className="size-4" strokeWidth={1.75} />
        </IconButton>
      </div>
    </div>
  );
}

export function Sidebar({ isOpen, onClose, ...contentProps }: SidebarProps) {
  // En móvil el panel es un modal de verdad: atrapa el foco, se cierra con
  // Escape y lo devuelve al botón que lo abrió (ver useFocusTrap).
  const panelRef = useFocusTrap<HTMLElement>(isOpen, onClose);

  return (
    <>
      {/* Escritorio: columna fija. Sin borde derecho -- el sidebar se separa del
          lienzo por un cambio mínimo de superficie, no por una línea. */}
      <aside
        className="hidden h-dvh w-[var(--sidebar-width)] shrink-0 lg:block"
        aria-label="Panel de conversaciones"
      >
        <SidebarContent {...contentProps} onCloseMobile={onClose} />
      </aside>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px] lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={transition.micro}
              onClick={onClose}
              aria-hidden="true"
            />
            <motion.aside
              ref={panelRef}
              role="dialog"
              aria-modal="true"
              aria-label="Panel de conversaciones"
              tabIndex={-1}
              className="shadow-float fixed inset-y-0 left-0 z-50 w-[var(--sidebar-width)] outline-none lg:hidden"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ duration: 0.34, ease: EASE_STANDARD }}
            >
              <SidebarContent {...contentProps} onCloseMobile={onClose} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
