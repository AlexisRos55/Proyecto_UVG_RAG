import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { BookOpen, FileText, GraduationCap, ShieldCheck, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { CredentialsForm } from "@/features/auth/components/credentials-form";
import { useAuth } from "@/features/auth/auth-context";
import type { CredentialsFormValues } from "@/features/auth/schemas";
import { ApiError } from "@/shared/lib/api-client";

const FEATURES = [
  { icon: BookOpen, label: "Reglamentos y normativas" },
  { icon: GraduationCap, label: "Becas y beneficios" },
  { icon: ShieldCheck, label: "Seguro estudiantil" },
  { icon: FileText, label: "Trámites y procedimientos" },
] as const;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: (values: CredentialsFormValues) => login(values.email, values.password),
    onSuccess: () => navigate("/chat"),
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : "No se pudo iniciar sesión.";
      toast.error(message);
    },
  });

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden lg:flex lg:flex-col lg:justify-between lg:p-12">
        <img
          src="/brand/campus-altiplano-bg.jpg"
          alt=""
          className="absolute inset-0 size-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-br from-[#0C3D5B]/95 via-[#0C3D5B]/80 to-[#0C3D5B]/50" />

        <div className="relative flex items-start justify-between">
          <img
            src="/brand/logo-uvg-altiplano-horizontal-blanco.png"
            alt="Universidad del Valle de Guatemala, Campus Altiplano"
            className="h-12 w-auto"
          />
          <div className="max-w-[9rem] border-t border-white/40 pt-2 text-right text-sm font-medium text-white/80 italic">
            Excelencia que trasciende
          </div>
        </div>

        <div className="relative flex flex-col gap-8">
          <div className="flex flex-col gap-3">
            <h1 className="text-4xl leading-tight font-semibold text-white">
              Asistente Virtual
              <br />
              Institucional
            </h1>
            <p className="text-lg text-white/80">
              Tu aliado para una vida universitaria más informada
            </p>
          </div>

          <div className="grid grid-cols-2 gap-x-6 gap-y-5">
            {FEATURES.map(({ icon: Icon, label }) => (
              <div key={label} className="flex flex-col gap-2">
                <Icon className="size-6 text-white" strokeWidth={1.75} />
                <span className="text-sm font-medium text-white/90">{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative flex items-end justify-between text-xs font-medium tracking-widest text-white/70 uppercase">
          <div className="flex items-center gap-2">
            <span>Campus Altiplano</span>
            <span className="h-px w-8 bg-white/40" />
          </div>
          <div className="text-right leading-relaxed">
            Formando líderes
            <br />
            para un mejor mañana
          </div>
        </div>
      </div>

      <div className="flex min-w-0 items-center justify-center bg-muted/40 p-4 sm:p-8">
        <Card className="w-full min-w-0 max-w-md rounded-2xl py-8 shadow-xl ring-foreground/5">
          <CardContent className="flex flex-col gap-6">
            <div className="flex flex-col items-center gap-1 text-center">
              <img
                src="/brand/logo-uvg-altiplano-horizontal-verde.png"
                alt="Universidad del Valle de Guatemala"
                className="h-10 w-auto"
              />
              <span className="text-sm font-medium text-muted-foreground">Campus Altiplano</span>
            </div>

            <Separator />

            <div className="flex flex-col items-center gap-1 text-center">
              <h2 className="text-2xl font-semibold text-foreground">Bienvenido</h2>
              <p className="text-sm text-muted-foreground">
                Inicia sesión con tu correo institucional para continuar
              </p>
            </div>

            <CredentialsForm
              submitLabel="Iniciar sesión"
              pendingLabel="Ingresando..."
              isPending={mutation.isPending}
              onSubmit={(values) => mutation.mutate(values)}
            />

            <Separator />

            <div className="flex items-center justify-center gap-2 text-center text-xs text-muted-foreground">
              <Sparkles className="size-3.5 text-primary" />
              <span>
                Asistente Virtual UVG Altiplano
                <br />
                Potenciado por Inteligencia Artificial
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
