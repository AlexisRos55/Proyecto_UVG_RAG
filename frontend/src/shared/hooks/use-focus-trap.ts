import { useEffect, useRef } from "react";

/**
 * Comportamiento de diálogo modal para el panel lateral en móvil.
 *
 * El cajón se abría sobre la conversación sin ninguna de las garantías que un
 * modal necesita: `Escape` no lo cerraba, el tabulador seguía recorriendo el
 * hilo que había debajo —invisible pero enfocable— y al cerrarlo el foco se
 * perdía al principio del documento. Quien navega con teclado o con lector de
 * pantalla quedaba atrapado fuera de lo que acababa de abrir.
 *
 * Es una implementación mínima a propósito: el proyecto no usa una librería de
 * diálogos para esto y añadirla por un único panel no se justifica.
 */

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "textarea:not([disabled])",
  "select:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export function useFocusTrap<T extends HTMLElement>(isOpen: boolean, onClose: () => void) {
  const panelRef = useRef<T>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  // `onClose` suele llegar como una lambda nueva en cada render. Si el efecto
  // dependiera de ella, se desmontaría y volvería a montar constantemente: la
  // limpieza devolvería el foco al botón una y otra vez —robándoselo al panel
  // que acaba de abrirse— y el oyente de Escape se reinstalaría en medio. Vive
  // en una referencia para que el efecto dependa sólo de si el panel está
  // abierto, que es lo único que de verdad lo gobierna.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!isOpen) return;

    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;

    const panel = panelRef.current;
    // Se enfoca el propio panel y no su primer botón: así el lector de pantalla
    // anuncia el diálogo antes de leer un control aislado.
    panel?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }

      if (event.key !== "Tab" || !panel) return;

      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (element) => element.offsetParent !== null,
      );
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      // El ciclo se cierra a mano: sin esto el tabulador se escapa al contenido
      // de detrás, que está oculto visualmente pero sigue en el árbol.
      if (event.shiftKey && (active === first || active === panel)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      // Devolver el foco a quien abrió el panel es lo que permite seguir
      // navegando desde donde se estaba.
      previouslyFocusedRef.current?.focus();
    };
  }, [isOpen]);

  return panelRef;
}
