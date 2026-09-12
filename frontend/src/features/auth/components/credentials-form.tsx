import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { ArrowRight, LoaderCircle, Lock, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { InputField } from "@/features/auth/components/input-field";
import { PasswordField } from "@/features/auth/components/password-field";
import { credentialsSchema, type CredentialsFormValues } from "@/features/auth/schemas";

interface CredentialsFormProps {
  submitLabel: string;
  pendingLabel: string;
  isPending: boolean;
  onSubmit: (values: CredentialsFormValues) => void;
}

/**
 * Formulario de alta de cuenta (correo + contraseña). Comparte los campos con el portal de
 * acceso, pero no sus extras: "mantener sesión iniciada" y la recuperación de contraseña
 * pertenecen al inicio de sesión, no al registro. Ver `LoginForm`.
 */
export function CredentialsForm({
  submitLabel,
  pendingLabel,
  isPending,
  onSubmit,
}: CredentialsFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, dirtyFields },
  } = useForm<CredentialsFormValues>({
    resolver: zodResolver(credentialsSchema),
    defaultValues: { email: "", password: "" },
    // Se valida al enviar y, a partir de ahí, en cada pulsación: `onTouched` acusaría
    // "es obligatorio" con sólo tabular por un campo vacío, antes de que el usuario haya
    // tenido oportunidad de escribir.
    mode: "onSubmit",
    reValidateMode: "onChange",
  });

  return (
    <form className="flex flex-col gap-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <InputField
        label="Correo institucional"
        type="email"
        inputMode="email"
        placeholder="nombre@uvg.edu.gt"
        autoComplete="email"
        spellCheck={false}
        icon={<Mail />}
        error={errors.email?.message}
        isValid={Boolean(dirtyFields.email)}
        disabled={isPending}
        {...register("email")}
      />

      <PasswordField
        label="Contraseña"
        placeholder="Mínimo 8 caracteres"
        autoComplete="new-password"
        icon={<Lock />}
        error={errors.password?.message}
        disabled={isPending}
        {...register("password")}
      />

      <Button
        type="submit"
        disabled={isPending}
        aria-busy={isPending}
        className="mt-1 h-11 w-full gap-2 rounded-xl bg-uvg-accent bg-linear-to-b from-uvg-accent to-uvg-accent-strong text-[0.9375rem] font-semibold text-white shadow-[0_1px_0_rgb(255_255_255/0.18)_inset,0_8px_20px_-8px_rgb(0_140_54/0.7)] transition-all duration-200 hover:from-uvg-accent-strong hover:to-uvg-accent-strong focus-visible:ring-3 focus-visible:ring-uvg-accent/35 disabled:opacity-100 disabled:saturate-[0.85]"
      >
        {isPending ? (
          <>
            <LoaderCircle className="size-[1.05rem] animate-spin" aria-hidden="true" />
            {pendingLabel}
          </>
        ) : (
          <>
            {submitLabel}
            <ArrowRight className="size-[1.05rem]" aria-hidden="true" />
          </>
        )}
      </Button>
    </form>
  );
}
