import { useId } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { Check, LoaderCircle, Lock, LogIn, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { InputField } from "@/features/auth/components/input-field";
import { PasswordField } from "@/features/auth/components/password-field";
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas";

interface LoginFormProps {
  isPending: boolean;
  /** Mantiene el estado de éxito hasta que la navegación posterior desmonta el formulario. */
  isSuccess?: boolean;
  onSubmit: (values: LoginFormValues) => void;
  onForgotPassword: () => void;
}

export function LoginForm({ isPending, isSuccess = false, onSubmit, onForgotPassword }: LoginFormProps) {
  const {
    control,
    register,
    handleSubmit,
    formState: { errors, dirtyFields },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
    // Se valida al enviar y, a partir de ahí, en cada pulsación: `onTouched` acusaría
    // "es obligatorio" con sólo tabular por un campo vacío, antes de que el usuario haya
    // tenido oportunidad de escribir.
    mode: "onSubmit",
    reValidateMode: "onChange",
  });

  const rememberMeId = useId();
  // Bloquear también en éxito evita un segundo envío durante la navegación a /chat.
  const isLocked = isPending || isSuccess;

  return (
    <form className="flex flex-col gap-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <InputField
        label="Correo institucional"
        type="email"
        inputMode="email"
        placeholder="nombre@uvg.edu.gt"
        autoComplete="email"
        autoFocus
        spellCheck={false}
        icon={<Mail />}
        error={errors.email?.message}
        isValid={Boolean(dirtyFields.email)}
        disabled={isLocked}
        {...register("email")}
      />

      <PasswordField
        label="Contraseña"
        placeholder="••••••••"
        autoComplete="current-password"
        icon={<Lock />}
        error={errors.password?.message}
        disabled={isLocked}
        labelAction={
          <button
            type="button"
            onClick={onForgotPassword}
            className="rounded text-[0.8125rem] font-medium text-uvg-accent transition-colors duration-200 outline-none hover:text-uvg-accent-strong hover:underline focus-visible:ring-3 focus-visible:ring-uvg-accent/25 focus-visible:underline"
          >
            ¿Olvidaste tu contraseña?
          </button>
        }
        {...register("password")}
      />

      <div className="flex items-center gap-2.5">
        <Controller
          control={control}
          name="rememberMe"
          render={({ field }) => (
            <Checkbox
              id={rememberMeId}
              checked={field.value}
              onCheckedChange={(checked) => field.onChange(checked === true)}
              onBlur={field.onBlur}
              ref={field.ref}
              disabled={isLocked}
              className="size-[1.05rem] rounded-[5px] border-slate-300 data-[state=checked]:border-uvg-accent data-[state=checked]:bg-uvg-accent focus-visible:border-uvg-accent focus-visible:ring-uvg-accent/25"
            />
          )}
        />
        <label
          htmlFor={rememberMeId}
          className="cursor-pointer text-[0.8125rem] text-slate-600 select-none"
        >
          Mantener sesión iniciada
        </label>
      </div>

      <Button
        type="submit"
        disabled={isLocked}
        aria-busy={isPending}
        className="mt-1 h-11 w-full gap-2 rounded-xl bg-uvg-accent bg-linear-to-b from-uvg-accent to-uvg-accent-strong text-[0.9375rem] font-semibold text-white shadow-[0_1px_0_rgb(255_255_255/0.18)_inset,0_8px_20px_-8px_rgb(0_140_54/0.7)] transition-all duration-200 hover:from-uvg-accent-strong hover:to-uvg-accent-strong hover:shadow-[0_1px_0_rgb(255_255_255/0.18)_inset,0_12px_26px_-8px_rgb(0_140_54/0.85)] focus-visible:ring-3 focus-visible:ring-uvg-accent/35 disabled:opacity-100 disabled:saturate-[0.85]"
      >
        {isSuccess ? (
          <>
            <Check className="size-[1.05rem]" aria-hidden="true" strokeWidth={2.5} />
            Sesión iniciada
          </>
        ) : isPending ? (
          <>
            <LoaderCircle className="size-[1.05rem] animate-spin" aria-hidden="true" />
            Iniciando sesión...
          </>
        ) : (
          <>
            <LogIn className="size-[1.05rem]" aria-hidden="true" />
            Iniciar sesión
          </>
        )}
      </Button>
    </form>
  );
}
