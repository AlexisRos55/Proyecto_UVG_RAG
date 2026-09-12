import type { ReactNode } from "react";
import { LoaderCircle } from "lucide-react";
import { cn } from "cn";

import { Button } from "@/components/ui/button";

interface SocialLoginButtonProps {
  /** Logotipo del proveedor. Decorativo: el texto del botón ya lo nombra. */
  icon: ReactNode;
  label: string;
  onClick: () => void;
  isPending?: boolean;
  /** Id del mensaje que explica el resultado de pulsarlo, si lo hay. */
  describedBy?: string;
  className?: string;
}

/**
 * Acceso federado (SSO). Estilo secundario: nunca debe competir con el botón principal.
 *
 * Deliberadamente no se marca con `aria-disabled` cuando el proveedor todavía no está
 * habilitado: un control que se anuncia como deshabilitado pero responde al clic es
 * contradictorio para quien usa lector de pantalla. El botón está activo y, al pulsarlo,
 * quien lo llama muestra el mensaje que explica el estado del proveedor.
 */
export function SocialLoginButton({
  icon,
  label,
  onClick,
  isPending = false,
  describedBy,
  className,
}: SocialLoginButtonProps) {
  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      disabled={isPending}
      aria-describedby={describedBy}
      className={cn(
        "h-11 w-full gap-2.5 rounded-xl border-slate-200 bg-white text-[0.9375rem] font-medium text-slate-700 shadow-[0_1px_2px_rgb(15_23_42/0.04)] transition-all duration-200",
        "hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900",
        "focus-visible:border-uvg-accent focus-visible:ring-3 focus-visible:ring-uvg-accent/20",
        className,
      )}
    >
      {isPending ? (
        <LoaderCircle className="size-[1.05rem] animate-spin" aria-hidden="true" />
      ) : (
        <span className="flex size-[1.05rem] items-center justify-center">{icon}</span>
      )}
      {label}
    </Button>
  );
}
