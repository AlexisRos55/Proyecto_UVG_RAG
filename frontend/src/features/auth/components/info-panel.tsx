import type { ReactNode } from "react";
import { ShieldCheck } from "lucide-react";
import { cn } from "cn";

interface InfoPanelProps {
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Aviso informativo de baja jerarquía (no es un error): fondo azul muy tenue, sin borde duro. */
export function InfoPanel({ icon, children, className }: InfoPanelProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-2.5 rounded-xl bg-uvg-accent-soft px-3.5 py-3 ring-1 ring-uvg-accent/10",
        className,
      )}
    >
      <span aria-hidden="true" className="mt-px flex text-uvg-accent [&_svg]:size-4">
        {icon ?? <ShieldCheck />}
      </span>
      <p className="text-[0.78125rem] leading-5 text-slate-600">{children}</p>
    </div>
  );
}
