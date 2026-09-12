import { useId, type ComponentProps, type ReactNode } from "react";
import { Check } from "lucide-react";
import { cn } from "cn";

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
 * seguir siendo neutro: la altura, el azul de acción y la validación son decisiones de esta
 * superficie de marca, no del sistema de diseño base.
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
          className={cn("text-[0.8125rem] text-slate-700", disabled && "opacity-60")}
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
              "pointer-events-none absolute top-1/2 left-3.5 flex -translate-y-1/2 text-slate-400 transition-colors duration-200",
              "[&_svg]:size-[1.05rem]",
              hasError && "text-destructive/70",
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
            "h-11 rounded-xl border-slate-200 bg-white text-[0.9375rem] text-slate-900 shadow-[0_1px_2px_rgb(15_23_42/0.04)]",
            "placeholder:text-slate-400",
            "transition-[color,background-color,border-color,box-shadow] duration-200",
            "hover:border-slate-300",
            "focus-visible:border-uvg-accent focus-visible:ring-3 focus-visible:ring-uvg-accent/15",
            "disabled:bg-slate-50 disabled:text-slate-400",
            "aria-invalid:border-destructive/60 aria-invalid:ring-destructive/15 aria-invalid:hover:border-destructive/70",
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
            className="absolute top-1/2 right-3.5 flex -translate-y-1/2 text-emerald-600"
          >
            <Check className="size-4" strokeWidth={2.5} />
          </span>
        ) : null}
      </div>

      <FieldError id={errorId} message={error} />
    </div>
  );
}
