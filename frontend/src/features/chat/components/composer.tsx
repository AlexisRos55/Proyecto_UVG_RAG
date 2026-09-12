import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp } from "lucide-react";
import { cn } from "cn";

import { transition } from "@/design-system/motion";

interface ComposerProps {
  disabled: boolean;
  onSend: (question: string) => void;
}

const MAX_HEIGHT_PX = 200;

export function Composer({ disabled, onSend }: ComposerProps) {
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

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

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
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Pregunta lo que necesites…"
            rows={1}
            disabled={disabled}
            aria-label="Escribe tu consulta"
            className="text-body placeholder:text-muted-foreground/55 min-h-9 flex-1 resize-none bg-transparent py-1.5 outline-none disabled:opacity-60"
          />

          <AnimatePresence initial={false}>
            {canSend && (
              <motion.button
                type="button"
                onClick={submit}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                whileTap={{ scale: 0.9 }}
                transition={transition.spring}
                className="bg-primary text-primary-foreground focus-visible:ring-ring flex size-9 shrink-0 items-center justify-center rounded-full focus-visible:ring-2 focus-visible:outline-none"
                aria-label="Enviar pregunta"
              >
                <ArrowUp className="size-4" strokeWidth={2.25} />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        <AnimatePresence>
          {isFocused && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={transition.micro}
              className="text-micro text-muted-foreground/50 mt-2.5 text-center tracking-normal"
            >
              Enter para enviar · Shift + Enter para una nueva línea
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
