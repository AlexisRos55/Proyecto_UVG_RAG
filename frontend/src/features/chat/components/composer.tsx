import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Loader2 } from "lucide-react";
import { cn } from "@/design-system/cn";

import { transition } from "@/design-system/motion";

interface ComposerProps {
  /** En curso un envío: el campo sigue editable, pero no se puede mandar otra. */
  isSending: boolean;
  /** Sin servidor no hay nada que enviar; se dice antes, no al fallar. */
  isOffline: boolean;
  /**
   * Devuelve si la consulta llegó a enviarse. Si no, el compositor recupera el
   * texto: antes una caída del servidor borraba la pregunta que el estudiante
   * acababa de escribir, y no había forma de recuperarla más que reescribirla.
   */
  onSend: (question: string) => Promise<boolean>;
}

const MAX_HEIGHT_PX = 200;

export function Composer({ isSending, isOffline, onSend }: ComposerProps) {
  const [value, setValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-crecimiento medido en JS y no con `field-sizing`, que sólo existe en
  // Chromium: en Safari y Firefox el campo se quedaría a una sola línea.
  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  const canSend = value.trim().length > 0 && !isSending && !isOffline;

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || !canSend) return;
    // Se vacía de inmediato porque la pregunta ya aparece en el hilo: dejarla
    // también en el campo haría dudar de si se envió.
    setValue("");
    const sent = await onSend(trimmed);
    if (!sent) {
      setValue(trimmed);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  };

  return (
    <div className="relative shrink-0 px-4 pb-5 sm:px-8 sm:pb-7">
      {/* Difuminado que funde el final de la conversación con el compositor: el
          texto no se corta en seco al hacer scroll. */}
      <div
        className="from-background pointer-events-none absolute inset-x-0 -top-16 h-16 bg-gradient-to-t to-transparent"
        aria-hidden="true"
      />

      <div className="mx-auto w-full max-w-[var(--measure)]">
        <div
          className={cn(
            "bg-surface-raised flex items-end gap-2 rounded-[1.375rem] py-2 pr-2 pl-4",
            "shadow-float transition-all duration-300 ease-standard",
            isFocused && "ring-primary/25 ring-2",
            isOffline && "opacity-60",
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={
              isOffline ? "Sin conexión con el servidor…" : "Pregunta lo que necesites…"
            }
            rows={1}
            disabled={isOffline}
            aria-label="Escribe tu consulta"
            className="text-body placeholder:text-text-tertiary min-h-9 flex-1 resize-none bg-transparent py-1.5 outline-none disabled:cursor-not-allowed"
          />

          {/* El botón ya no desaparece durante el envío. Antes, al enviar,
              `canSend` pasaba a falso y el botón se desmontaba: quedaba un campo
              vacío sin ningún rastro de que algo estuviera ocurriendo. Ahora
              permanece y cambia de estado, que es lo que hace visible el
              progreso. */}
          <AnimatePresence initial={false}>
            {(canSend || isSending) && (
              <motion.button
                type="button"
                onClick={() => void submit()}
                disabled={!canSend}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                whileTap={canSend ? { scale: 0.9 } : undefined}
                transition={transition.spring}
                className="bg-primary text-primary-foreground focus-visible:ring-ring flex size-9 shrink-0 items-center justify-center rounded-full transition-opacity duration-200 focus-visible:ring-2 focus-visible:outline-none disabled:opacity-70"
                aria-label={isSending ? "Enviando la consulta" : "Enviar pregunta"}
              >
                {isSending ? (
                  <Loader2 className="size-4 animate-spin" strokeWidth={2.25} />
                ) : (
                  <ArrowUp className="size-4" strokeWidth={2.25} />
                )}
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* La pista se mantiene montada y sólo cambia de opacidad. Montándola al
            enfocar, el compositor entero daba un salto de una línea cada vez que
            el campo recibía el cursor. */}
        <p
          aria-hidden={!isFocused}
          className={cn(
            "text-micro text-text-tertiary mt-2.5 hidden text-center tracking-normal transition-opacity duration-200 ease-soft sm:block",
            isFocused ? "opacity-100" : "opacity-0",
          )}
        >
          Enter para enviar · Shift + Enter para una nueva línea
        </p>
      </div>
    </div>
  );
}
