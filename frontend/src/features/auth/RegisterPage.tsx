import { useMutation } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CredentialsForm } from "@/features/auth/components/credentials-form";
import { useAuth } from "@/features/auth/auth-context";
import type { CredentialsFormValues } from "@/features/auth/schemas";
import { ApiError } from "@/shared/lib/api-client";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: (values: CredentialsFormValues) => register(values.email, values.password),
    onSuccess: () => navigate("/chat"),
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : "No se pudo completar el registro.";
      toast.error(message);
    },
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Crear cuenta</CardTitle>
          <CardDescription>Regístrate con tu correo institucional @uvg.edu.gt.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <CredentialsForm
            submitLabel="Registrarme"
            pendingLabel="Creando cuenta..."
            isPending={mutation.isPending}
            onSubmit={(values) => mutation.mutate(values)}
          />
          <p className="text-center text-sm text-muted-foreground">
            ¿Ya tienes cuenta?{" "}
            <Link to="/login" className="font-medium text-foreground underline">
              Inicia sesión
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
