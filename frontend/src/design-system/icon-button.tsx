import type { ComponentProps } from "react";
import { cn } from "cn";

interface IconButtonProps extends Omit<ComponentProps<"button">, "aria-label"> {
  /** Obligatorio: estos botones no tienen texto visible. */
  label: string;
  size?: "sm" | "md";
}

/**
 * Botón de solo icono, sin borde ni relleno en reposo. Es el único tratamiento
 * de acción secundaria del sistema: menú, cerrar, tema, salir. Antes cada uno
 * repetía sus propias clases y divergían poco a poco.
 */
export function IconButton({ label, size = "md", className, ...props }: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-lg text-muted-foreground",
        "transition-all duration-150 ease-soft",
        "hover:bg-foreground/[0.06] hover:text-foreground active:scale-95",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        size === "sm" ? "size-7" : "size-8",
        className,
      )}
      {...props}
    />
  );
}
