import { useId, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { ArrowRight, Eye, EyeOff, Lock, Mail } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { credentialsSchema, type CredentialsFormValues } from "@/features/auth/schemas";

interface CredentialsFormProps {
  submitLabel: string;
  pendingLabel: string;
  isPending: boolean;
  onSubmit: (values: CredentialsFormValues) => void;
}

export function CredentialsForm({
  submitLabel,
  pendingLabel,
  isPending,
  onSubmit,
}: CredentialsFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CredentialsFormValues>({
    resolver: zodResolver(credentialsSchema),
    defaultValues: { email: "", password: "" },
  });
  const [showPassword, setShowPassword] = useState(false);
  const rememberMeId = useId();

  return (
    <form className="flex flex-col gap-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">Correo institucional</Label>
        <div className="relative">
          <Mail className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="email"
            type="email"
            placeholder="nombre.apellido@uvg.edu.gt"
            autoComplete="email"
            aria-invalid={Boolean(errors.email)}
            className="h-11 pl-9"
            {...register("email")}
          />
        </div>
        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="password">Contraseña</Label>
        <div className="relative">
          <Lock className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="password"
            type={showPassword ? "text" : "password"}
            placeholder="Ingresa tu contraseña"
            autoComplete="current-password"
            aria-invalid={Boolean(errors.password)}
            className="h-11 pr-10 pl-9"
            {...register("password")}
          />
          <button
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            className="absolute top-1/2 right-3 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
            aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            tabIndex={-1}
          >
            {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 text-sm">
        <label htmlFor={rememberMeId} className="flex items-center gap-2 text-muted-foreground">
          <Checkbox id={rememberMeId} />
          Mantener sesión iniciada
        </label>
        <button
          type="button"
          onClick={() =>
            toast.info("Esta función estará disponible próximamente. Contacta a soporte académico.")
          }
          className="font-medium text-primary hover:underline"
        >
          ¿Olvidaste tu contraseña?
        </button>
      </div>

      <Button type="submit" disabled={isPending} size="lg" className="h-11 justify-between">
        {isPending ? pendingLabel : submitLabel}
        <ArrowRight className="size-4" />
      </Button>
    </form>
  );
}
