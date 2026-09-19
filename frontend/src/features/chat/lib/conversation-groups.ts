/**
 * Agrupa conversaciones en tramos temporales («Hoy», «Ayer», «Esta semana»…).
 *
 * Hoy el backend sostiene un único hilo activo por estudiante (FR-14), así que
 * el resultado casi siempre es un grupo con un elemento. Aun así la etiqueta
 * deja de ser un rótulo fijo («Reciente») y pasa a decir algo verdadero sobre lo
 * que hay debajo — y el día que exista historial múltiple la vista no cambia.
 *
 * Los tramos se calculan sobre días naturales, no sobre horas transcurridas: a
 * las 00:30 del martes, algo de las 23:00 del lunes es «Ayer», no «Hoy». Es como
 * lee las fechas una persona, y es lo que hacen los clientes de correo.
 */

export type ConversationBucket = "today" | "yesterday" | "week" | "month" | "older";

const BUCKET_LABEL: Record<ConversationBucket, string> = {
  today: "Hoy",
  yesterday: "Ayer",
  week: "Esta semana",
  month: "Este mes",
  older: "Más antiguas",
};

/** Orden de presentación: de lo más reciente a lo más antiguo. */
const BUCKET_ORDER: ConversationBucket[] = ["today", "yesterday", "week", "month", "older"];

const MS_PER_DAY = 86_400_000;

/** Medianoche local del día al que pertenece la fecha. */
function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

export function bucketFor(isoDate: string, now: Date = new Date()): ConversationBucket {
  const date = new Date(isoDate);
  // Una fecha ilegible no debe tirar la lista entera: cae al tramo más antiguo.
  if (Number.isNaN(date.getTime())) return "older";

  const daysApart = Math.round((startOfDay(now) - startOfDay(date)) / MS_PER_DAY);

  if (daysApart <= 0) return "today";
  if (daysApart === 1) return "yesterday";
  if (daysApart < 7) return "week";
  if (daysApart < 30) return "month";
  return "older";
}

export interface ConversationGroup<T> {
  bucket: ConversationBucket;
  label: string;
  items: T[];
}

/**
 * Devuelve sólo los grupos que tienen contenido, en orden cronológico inverso.
 * Un encabezado vacío es ruido: si no hay nada de ayer, «Ayer» no se dibuja.
 */
export function groupByDate<T extends { updatedAt: string }>(
  conversations: readonly T[],
  now: Date = new Date(),
): ConversationGroup<T>[] {
  const byBucket = new Map<ConversationBucket, T[]>();

  for (const conversation of conversations) {
    const bucket = bucketFor(conversation.updatedAt, now);
    const existing = byBucket.get(bucket);
    if (existing) existing.push(conversation);
    else byBucket.set(bucket, [conversation]);
  }

  return BUCKET_ORDER.filter((bucket) => byBucket.has(bucket)).map((bucket) => ({
    bucket,
    label: BUCKET_LABEL[bucket],
    // Dentro del tramo, lo último tocado primero.
    items: byBucket
      .get(bucket)!
      .slice()
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
  }));
}
