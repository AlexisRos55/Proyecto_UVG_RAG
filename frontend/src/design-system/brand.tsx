import { useId } from "react";
import { cn } from "cn";

/**
 * Identidad de UVG AI.
 *
 * Se distinguen dos marcas con papeles distintos y deliberadamente separados:
 *
 * - `BrandLockup`  — identidad institucional + nombre de producto. Usa el
 *   logotipo oficial de la universidad, pequeño, como icono de aplicación.
 * - `BrandGlyph`   — presencia del asistente (la "V" de Valle trazada como un
 *   destello). No representa a la universidad, representa a la IA, y por eso
 *   puede tener gradiente y movimiento sin contradecir el manual de marca.
 */

export function BrandGlyph({ className }: { className?: string }) {
  const gradientId = useId();

  return (
    <svg viewBox="0 0 40 40" className={className} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="6" y1="4" x2="34" y2="34" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--brand-from)" />
          <stop offset="1" stopColor="var(--brand-to)" />
        </linearGradient>
      </defs>
      <path
        d="M8.5 10.5 L20 31 L31.5 10.5"
        stroke={`url(#${gradientId})`}
        strokeWidth="3.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface BrandLockupProps {
  className?: string;
  /** Reduce el lockup a logotipo + nombre, sin la atribución institucional. */
  compact?: boolean;
}

/**
 * Lockup de servicio, construido según la "versión tipográfica" del manual (pág. 4):
 * *"la versión más minimalista del logotipo, perfecta para complementar logos o nombres
 * de otros servicios que se deseen comunicar dentro del contexto de UVG"*.
 *
 * El logotipo cuadrado va pequeño y con su área de resguardo (pág. 6: el aire alrededor
 * equivale a la altura de la "U"; aquí, ≥50% de su propio tamaño). Debajo del nombre del
 * servicio, la atribución completa ancla la marca madre — que es justamente lo que el
 * manual exige a los servicios independientes (pág. 9).
 */
export function BrandLockup({ className, compact = false }: BrandLockupProps) {
  return (
    <div className={cn("flex min-w-0 items-center gap-2.5", className)}>
      <img
        src="/brand/logo-uvg-altiplano.png"
        alt="Universidad del Valle de Guatemala"
        className="shadow-soft size-8 shrink-0 rounded-[0.5rem]"
      />
      <span className="flex min-w-0 flex-col gap-1">
        <span className="text-foreground text-[0.9375rem] leading-none font-semibold tracking-[-0.015em]">
          UVG <span className="text-primary">AI</span>
        </span>
        {!compact && (
          <span className="text-micro text-muted-foreground/60 flex flex-col leading-[1.35] tracking-normal normal-case">
            <span className="truncate">Universidad del Valle de Guatemala</span>
            <span className="truncate">Campus Altiplano</span>
          </span>
        )}
      </span>
    </div>
  );
}
