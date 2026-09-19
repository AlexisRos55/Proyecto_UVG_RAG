import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Comportamiento de desplazamiento del hilo.
 *
 * Antes se llamaba a `scrollIntoView({ behavior: "smooth" })` sobre un centinela
 * cada vez que cambiaba el número de mensajes. Eso producía dos defectos que
 * delatan un prototipo:
 *
 *  1. Al abrir la aplicación el historial aparecía arriba y **se animaba** hasta
 *     el final. Una conversación ya existente debe estar donde la dejaste, no
 *     viajar delante de ti.
 *  2. Si subías a releer una respuesta y llegaba cualquier render, el hilo te
 *     devolvía al final de un tirón. El usuario perdía su sitio sin pedirlo.
 *
 * La regla correcta —la de cualquier cliente de mensajería— es: salto seco la
 * primera vez, y desplazamiento suave después **sólo si ya estabas al final**.
 * Si te habías alejado, no se toca nada y aparece un botón para volver.
 */

/** Margen para considerar «al final»: un par de líneas de holgura. */
const AT_BOTTOM_THRESHOLD_PX = 120;

export function useThreadScroll(dependencies: readonly unknown[]) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const hasAnchoredRef = useRef(false);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const container = containerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior });
  }, []);

  const scrollToTop = useCallback(() => {
    containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  // Estado «al final», derivado del propio scroll y no de un contador.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const update = () => {
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      setIsAtBottom(distanceFromBottom <= AT_BOTTOM_THRESHOLD_PX);
    };

    update();
    container.addEventListener("scroll", update, { passive: true });
    return () => container.removeEventListener("scroll", update);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Primer contenido real: se aterriza al final sin animación. `scrollHeight`
    // mayor que el alto visible es la señal de que ya hay hilo que medir; hasta
    // entonces (pantalla de bienvenida, carga) no hay nada a lo que anclarse.
    if (!hasAnchoredRef.current) {
      if (container.scrollHeight > container.clientHeight) {
        hasAnchoredRef.current = true;
        scrollToBottom("auto");
      }
      return;
    }

    if (isAtBottom) scrollToBottom("smooth");
    // `isAtBottom` se lee, pero no debe disparar el efecto: volver al final es
    // consecuencia de que llegue contenido nuevo, no de que el usuario baje.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, scrollToBottom]);

  return { containerRef, isAtBottom, scrollToBottom, scrollToTop };
}
