import { Info } from "lucide-react";

/**
 * Aviso discreto para quien usa Alexis como visitante (ADR-0019). Vive junto al
 * compositor, como el aviso de conexión: siempre a la vista, sin interrumpir la
 * conversación ni competir con ella.
 */
export function GuestNotice() {
  return (
    <p className="text-micro text-text-tertiary mx-auto flex w-full max-w-[var(--measure)] shrink-0 items-center justify-center gap-1.5 px-4 pb-1 text-center tracking-normal sm:px-8">
      <Info className="size-3.5 shrink-0" aria-hidden="true" />
      Estás utilizando Alexis como visitante. Algunas funciones están disponibles únicamente para
      usuarios institucionales.
    </p>
  );
}
