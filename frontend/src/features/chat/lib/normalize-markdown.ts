/**
 * Red de seguridad entre el modelo y el renderizador.
 *
 * El prompt pide Markdown válido, pero un modelo generativo no es un contrato:
 * en producción emitía el carácter `•` literal, que react-markdown trata como
 * texto y convierte cada elemento en un párrafo suelto. El resultado se veía
 * peor que sin instrucción de formato.
 *
 * Estas transformaciones son conservadoras: solo actúan sobre patrones que no
 * pueden significar otra cosa al inicio de una línea.
 */

/** Viñetas tipográficas al inicio de línea → viñeta Markdown. */
const TYPOGRAPHIC_BULLET = /^([^\S\n]*)[•·▪◦‣–—][^\S\n]+/gm;

/** `1)` en vez de `1.` — variante frecuente que Markdown no reconoce. */
const PAREN_ORDERED = /^([^\S\n]*)(\d{1,2})\)[^\S\n]+/gm;

/** Encabezado sin espacio tras las almohadillas: `##Título`. */
const TIGHT_HEADING = /^(#{1,6})([^\s#])/gm;

/**
 * Una lista pegada al párrafo anterior no se reconoce como lista.
 *
 * La línea previa debe NO ser a su vez un elemento de lista: sin esa condición
 * la regla separa los elementos entre sí y parte una lista en varias.
 */
const LIST_NEEDS_BLANK_LINE = /^(?![^\S\n]*(?:[-*+]|\d{1,2}[.)])[^\S\n])(.+)\n(?=[^\S\n]*(?:[-*+]|\d{1,2}[.)])[^\S\n])/gm;

/** Tres o más saltos seguidos: el ritmo vertical lo define la hoja de estilos. */
const EXCESS_BLANK_LINES = /\n{3,}/g;

export function normalizeMarkdown(raw: string): string {
  return raw
    .replace(TYPOGRAPHIC_BULLET, "$1- ")
    .replace(PAREN_ORDERED, "$1$2. ")
    .replace(TIGHT_HEADING, "$1 $2")
    .replace(LIST_NEEDS_BLANK_LINE, "$1\n\n")
    .replace(EXCESS_BLANK_LINES, "\n\n")
    .trim();
}

/**
 * Texto plano para el portapapeles.
 *
 * Copiar Markdown crudo obliga al estudiante a limpiar `**` y `-` a mano antes
 * de pegarlo en un correo. Se conserva la estructura de lista con viñetas
 * tipográficas, que sí se leen bien fuera de un renderizador.
 */
export function markdownToPlainText(raw: string): string {
  return normalizeMarkdown(raw)
    .replace(/^#{1,6}[^\S\n]+/gm, "")
    .replace(/^[^\S\n]*[-*+][^\S\n]+/gm, "• ")
    .replace(/^[^\S\n]*>[^\S\n]?/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/(?<!\w)_([^_\n]+)_(?!\w)/g, "$1")
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    // Las tablas pierden su rejilla: se deja cada fila como valores separados.
    .replace(/^\|(.+)\|$/gm, (_, row: string) =>
      row
        .split("|")
        .map((cell) => cell.trim())
        .filter(Boolean)
        .join(" · "),
    )
    .replace(/^[\s|:-]*-{3,}[\s|:-]*$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
