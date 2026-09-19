import { useId, type ComponentProps, type ReactNode } from "react";
import { Check } from "lucide-react";
import { cn } from "@/design-system/cn";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FieldError } from "@/features/auth/components/field-error";

export interface InputFieldProps extends Omit<ComponentProps<"input">, "children"> {
  label: string;
  /** Icono decorativo al inicio del campo. */
  icon?: ReactNode;
  /** Control al final del campo (p. ej. mostrar/ocultar contraseña). */
  endAdornment?: ReactNode;
  /** Acción secundaria alineada a la derecha de la etiqueta. */
  labelAction?: ReactNode;
  error?: string;
  /** Muestra la marca de validación. Sólo tiene efecto si no hay error. */
  isValid?: boolean;
}

/**
 * Campo de texto del portal de acceso: etiqueta, icono, estados (hover / focus / disabled /
 * error / éxito) y el cableado ARIA que conecta el input con su mensaje de error.
 *
 * Existe como pieza aparte de `Input` porque `Input` es el primitivo de shadcn/ui y debe
 * seguir siendo neutro: la altura, el acento y la validación son decisiones de esta
 * superficie de marca, no del sistema de diseño base.
 *
 * Todos sus colores provienen de tokens semánticos. Antes estaban cableados a la
 * paleta `slate` del modo claro, de modo que en la pantalla de registro —que sí
 * responde al tema— el texto tecleado quedaba a 1.05:1 sobre el fondo oscuro: el
 * usuario no podía leer lo que escribía. Ningún control de formulario debe
 * declarar un color literal.
 */
export function InputField({
  label,
  icon,
  endAdornment,
  labelAction,
  error,
  isValid = false,
  id,
  className,
  disabled,
  ...inputProps
}: InputFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = `${inputId}-error`;
  const hasError = Boolean(error);
  const showValid = isValid && !hasError;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-3">
        <Label
          htmlFor={inputId}
          className={cn("text-caption text-foreground font-medium", disabled && "opacity-60")}
        >
          {label}
        </Label>
        {labelAction}
      </div>

      <div className="relative">
        {icon ? (
          <span
            aria-hidden="true"
            className={cn(
              "text-muted-foreground pointer-events-none absolute top-1/2 left-3.5 flex -translate-y-1/2 transition-colors duration-200",
              "[&_svg]:size-[1.05rem]",
              hasError && "text-destructive",
            )}
          >
            {icon}
          </span>
        ) : null}

        <Input
          id={inputId}
          disabled={disabled}
          aria-invalid={hasError || undefined}
          aria-describedby={hasError ? errorId : undefined}
          className={cn(
            "border-input bg-card text-foreground shadow-soft h-11 rounded-xl text-[0.9375rem]",
            "placeholder:text-muted-foreground",
            "transition-[color,background-color,border-color,box-shadow] duration-200",
            "hover:border-ring/50",
            "focus-visible:border-primary focus-visible:ring-primary/25 focus-visible:ring-3",
            "disabled:bg-muted disabled:text-muted-foreground",
            "aria-invalid:border-destructive aria-invalid:ring-destructive/20",
            icon ? "pl-10" : "pl-3.5",
            endAdornment || showValid ? "pr-11" : "pr-3.5",
            className,
          )}
          {...inputProps}
        />

        {endAdornment ? (
          <span className="absolute top-1/2 right-1.5 flex -translate-y-1/2">{endAdornment}</span>
        ) : showValid ? (
          <span
            aria-hidden="true"
            className="text-primary absolute top-1/2 right-3.5 flex -translate-y-1/2"
          >
            <Check className="size-4" strokeWidth={2.5} />
          </span>
        ) : null}
      </div>

      <FieldError id={errorId} message={error} />
    </div>
  );
}
