const TITLE_MAX_LENGTH = 38;

/**
 * Título corto para el historial, derivado de la primera pregunta del estudiante.
 *
 * Se conserva la pregunta tal cual (sólo normalizada y truncada) en lugar de
 * recortar el interrogativo: quitar "¿Qué" dejaba el verbo colgando y producía
 * títulos como "Becas y beneficios ofrece …". La pregunta literal se lee mejor
 * y es lo que hacen los productos de chat cuando no resumen con un modelo.
 */
export function generateConversationTitle(firstQuestion: string): string {
  const normalized = firstQuestion.replace(/\s+/g, " ").trim();
  if (normalized.length <= TITLE_MAX_LENGTH) return normalized;
  // Corta en el último espacio para no partir una palabra por la mitad.
  const truncated = normalized.slice(0, TITLE_MAX_LENGTH);
  const lastSpace = truncated.lastIndexOf(" ");
  return `${(lastSpace > 20 ? truncated.slice(0, lastSpace) : truncated).trimEnd()}…`;
}

/** Nombre para el saludo, derivado del correo institucional
 * ("alexis.rosales@uvg.edu.gt" -> "Alexis"). Sin endpoint de perfil en el
 * backend, el correo es el único dato de identidad disponible. */
export function displayNameFromEmail(email: string): string {
  const localPart = email.split("@")[0] ?? "";
  const firstName = localPart.split(/[._-]/)[0] ?? "";
  if (!firstName) return "";
  return firstName.charAt(0).toUpperCase() + firstName.slice(1).toLowerCase();
}

const RELATIVE_UNITS: [seconds: number, label: string][] = [
  [60, "Justo ahora"],
  [3600, "min"],
  [86400, "h"],
  [86400 * 2, "Ayer"],
];

/** Fecha relativa compacta ("Hace 5 min", "Ayer", "Hace 3 días") sin sumar date-fns solo
 * por esto — el dominio de valores es acotado (mensajes de una sesión de estudio). */
export function formatRelativeDate(isoDate: string): string {
  const diffSeconds = (Date.now() - new Date(isoDate).getTime()) / 1000;
  if (diffSeconds < RELATIVE_UNITS[0][0]) return "Justo ahora";
  if (diffSeconds < RELATIVE_UNITS[1][0]) return `Hace ${Math.floor(diffSeconds / 60)} min`;
  if (diffSeconds < RELATIVE_UNITS[2][0]) return `Hace ${Math.floor(diffSeconds / 3600)} h`;
  if (diffSeconds < RELATIVE_UNITS[3][0]) return "Ayer";
  return `Hace ${Math.floor(diffSeconds / 86400)} días`;
}
