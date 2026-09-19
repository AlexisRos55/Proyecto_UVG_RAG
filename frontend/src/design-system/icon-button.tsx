import type { ComponentProps } from "react";
import { Slot } from "radix-ui";
import { cn } from "@/design-system/cn";

interface IconButtonProps extends Omit<ComponentProps<"button">, "aria-label"> {
  /** Obligatorio: estos botones no tienen texto visible. */
  label: string;
  size?: "sm" | "md";
  /** Delega el renderizado al hijo (p. ej. un `Link`) conservando los estilos. */
  asChild?: boolean;
}

/**
 * Botón de solo icono, sin borde ni relleno en reposo. Es el único tratamiento
 * de acción secundaria del sistema: menú, cerrar, tema, salir, reindexar.
 *
 * El área táctil real es de 40px aunque el fondo visible sea menor: el objetivo
 * mínimo recomendado es 44px y un icono de 28px resulta difícil de acertar con
 * el pulgar.
 */
export function IconButton({
  label,
  size = "md",
  className,
  asChild = false,
  ...props
}: IconButtonProps) {
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      // `type` solo aplica a un <button> real; con asChild el hijo define su semántica.
      {...(asChild ? {} : { type: "button" as const })}
      aria-label={label}
      title={label}
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-lg text-muted-foreground",
        "transition-all duration-150 ease-soft",
        "hover:bg-foreground/[0.06] hover:text-foreground active:scale-95",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        "disabled:pointer-events-none disabled:opacity-40",
        // Amplía el área de pulsación sin alterar la composición visual.
        "after:absolute after:left-1/2 after:top-1/2 after:size-11 after:-translate-x-1/2 after:-translate-y-1/2 after:content-['']",
        size === "sm" ? "size-8" : "size-9",
        className,
      )}
      {...props}
    />
  );
}
