import { Skeleton } from "@/design-system/states";

/**
 * Carga del historial con la forma de lo que va a aparecer.
 *
 * Antes era una línea de texto centrada («Cargando conversación…») en una
 * pantalla por lo demás vacía: el salto al hilo real era un cambio de página
 * completo. Un esqueleto con la silueta del turno —titular de la pregunta, tres
 * líneas de respuesta— hace que la llegada del contenido sea una sustitución y
 * no un sobresalto, que es lo que reduce la sensación de espera.
 */
export function ThreadSkeleton() {
  return (
    <div
      className="mx-auto w-full max-w-[var(--measure)] px-6 pt-10 pb-16 sm:px-8"
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Cargando la conversación…</span>

      {[0, 1].map((turn) => (
        <div key={turn} className={turn === 0 ? "" : "mt-16"}>
          {/* Pregunta: un titular corto. */}
          <Skeleton className="h-6 w-[min(28rem,78%)] rounded-lg" />

          {/* Respuesta: tres líneas de cuerpo con el ritmo real de lectura. */}
          <div className="mt-7 flex flex-col gap-3">
            <Skeleton className="h-4 w-full rounded-md" />
            <Skeleton className="h-4 w-[94%] rounded-md" />
            <Skeleton className="h-4 w-[62%] rounded-md" />
          </div>
        </div>
      ))}
    </div>
  );
}
