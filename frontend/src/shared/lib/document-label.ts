import { documentDisplayName } from "@/shared/lib/document-name";

/**
 * Convierte el nombre de archivo en una referencia documental presentable.
 *
 * Los nombres reales del corpus son códigos internos —«UVG.DAF.02.001 Reglamento
 * ayudas financieras V 10.0  (27-5-26).pdf»— y mostrarlos tal cual hace que la
 * cita parezca la salida de un sistema de archivos en vez de una referencia.
 */

export type DocumentKind = "reglamento" | "calendario" | "proceso" | "plan" | "documento";

const KIND_LABEL: Record<DocumentKind, string> = {
  reglamento: "Reglamento",
  calendario: "Calendario",
  proceso: "Proceso",
  plan: "Plan de estudios",
  documento: "Documento oficial",
};

/** Código institucional al inicio: «UVG.DAF.02.001 », «UVG.VE.02.001 ». */
const INSTITUTIONAL_CODE = /^UVG(?:\.[A-Z]{1,4}){1,3}(?:\.\d{2,3})*\s*/i;
/** Versión y fecha de revisión al final: «V 10.0  (27-5-26)», «v2». */
const VERSION_SUFFIX = /\s*[-–]?\s*\bv(?:ersi[oó]n)?\.?\s*\d+(?:\.\d+)*\s*(?:\([^)]*\))?\s*$/i;
const TRAILING_DATE = /\s*\(\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s*\)\s*$/;
const EXTENSION = /\.(pdf|docx?|txt|md)$/i;

export function documentKind(rawName: string): DocumentKind {
  const name = documentDisplayName(rawName).toLowerCase();
  if (name.includes("reglamento") || name.includes("normativa")) return "reglamento";
  if (name.includes("calendario")) return "calendario";
  if (name.includes("proceso") || name.includes("admisi") || name.includes("inscripci"))
    return "proceso";
  if (name.includes("pensum") || name.includes("plan de estudio")) return "plan";
  return "documento";
}

export function documentKindLabel(rawName: string): string {
  return KIND_LABEL[documentKind(rawName)];
}

/** Título legible: sin extensión, sin código interno y sin sufijo de versión. */
export function documentTitle(rawName: string): string {
  const cleaned = documentDisplayName(rawName)
    .replace(EXTENSION, "")
    .replace(INSTITUTIONAL_CODE, "")
    .replace(TRAILING_DATE, "")
    .replace(VERSION_SUFFIX, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();

  if (!cleaned) return documentDisplayName(rawName);
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

type CitableSource = {
  document_name: string;
  page_number: number | null;
  document_title?: string | null;
  section?: string | null;
  page_end?: number | null;
};

/**
 * Título de la fuente. El backend ya envía el título que declara el propio
 * documento (membrete o metadatos del PDF); el nombre de archivo solo se
 * limpia como respaldo para mensajes anteriores a la Fase 9.
 */
export function sourceTitle(source: CitableSource): string {
  return source.document_title?.trim() || documentTitle(source.document_name);
}

/** «Capítulo IV · Artículo 18. Condiciones · págs. 10–11», o solo la página. */
export function sourceLocation(source: CitableSource): string | null {
  const parts: string[] = [];
  if (source.section) parts.push(source.section);
  if (source.page_number != null) {
    parts.push(
      source.page_end != null && source.page_end !== source.page_number
        ? `págs. ${source.page_number}–${source.page_end}`
        : `pág. ${source.page_number}`,
    );
  }
  return parts.length ? parts.join(" · ") : null;
}

/**
 * Descarta repeticiones del mismo documento conservando el orden de llegada.
 *
 * El orden que envía el backend ya es el de relevancia —los documentos aparecen
 * según el fragmento mejor puntuado que los cita—, así que preservarlo equivale
 * a ordenar por pertinencia. El corpus contiene duplicados reales, y sin esto
 * la misma referencia aparece dos veces bajo una respuesta.
 */
export function dedupeSources<T extends CitableSource>(sources: readonly T[]): T[] {
  const seen = new Set<string>();
  const unique: T[] = [];
  for (const source of sources) {
    // El apartado forma parte de la identidad: dos artículos del mismo
    // reglamento son dos referencias distintas.
    const key = `${sourceTitle(source).toLowerCase()}|${source.section ?? ""}|${source.page_number ?? ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(source);
  }
  return unique;
}
