import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle } from "lucide-react";

import { collapseFade } from "@/features/auth/animations";

interface FieldErrorProps {
  id: string;
  message?: string;
}

/**
 * Mensaje de validación de un campo. Se anuncia con `role="alert"` y se anima con un
 * colapso de altura para que la aparición del error no haga saltar el formulario.
 */
export function FieldError({ id, message }: FieldErrorProps) {
  return (
    <AnimatePresence initial={false}>
      {message ? (
        <motion.p
          key={message}
          id={id}
          role="alert"
          variants={collapseFade}
          initial="hidden"
          animate="visible"
          exit="exit"
          className="flex items-start gap-1.5 overflow-hidden text-[0.8125rem] leading-5 font-medium text-destructive"
        >
          <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>{message}</span>
        </motion.p>
      ) : null}
    </AnimatePresence>
  );
}
