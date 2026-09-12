import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import { InputField, type InputFieldProps } from "@/features/auth/components/input-field";

type PasswordFieldProps = Omit<InputFieldProps, "type" | "endAdornment">;

/**
 * Campo de contraseña con alternancia mostrar/ocultar.
 *
 * El botón es enfocable con teclado a propósito: es un control real y ocultarlo del orden
 * de tabulación deja a quien navega sin ratón sin forma de verificar lo que escribió.
 * `aria-pressed` comunica el estado y la etiqueta describe la acción, no el estado actual.
 */
export function PasswordField({ disabled, ...props }: PasswordFieldProps) {
  const [isVisible, setIsVisible] = useState(false);
  const Icon = isVisible ? EyeOff : Eye;

  return (
    <InputField
      {...props}
      disabled={disabled}
      type={isVisible ? "text" : "password"}
      endAdornment={
        <button
          type="button"
          onClick={() => setIsVisible((visible) => !visible)}
          disabled={disabled}
          aria-pressed={isVisible}
          aria-label={isVisible ? "Ocultar contraseña" : "Mostrar contraseña"}
          className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition-colors duration-200 outline-none hover:bg-slate-100 hover:text-slate-600 focus-visible:ring-3 focus-visible:ring-uvg-accent/25 focus-visible:text-slate-600 disabled:pointer-events-none disabled:opacity-50"
        >
          <Icon className="size-4" aria-hidden="true" />
        </button>
      }
    />
  );
}

export type { PasswordFieldProps };
