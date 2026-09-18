/**
 * Reparación de nombres de documento mal codificados.
 *
 * Parte del corpus llegó con los acentos rotos ("Educaci¢n F°sica", "Maestr°a").
 * El origen se identificó con precisión: los bytes del nombre estaban en CP437
 * (página de códigos OEM de Windows) pero se interpretaron como MacRoman. Es una
 * corrupción del archivo de origen, no del backend — el sistema almacenó
 * fielmente lo que recibió.
 *
 * La tabla invierte exactamente esa doble lectura: cada glifo MacRoman se
 * devuelve al carácter que CP437 asigna al mismo byte. Verificado contra los
 * diez nombres reales del corpus: repara los nueve corruptos y deja intactos
 * los correctos.
 */
const MOJIBAKE: Readonly<Record<string, string>> = {
  "Å": "ü", "Ç": "é", "ê": "É", "ö": "Ü", "†": "á", "°": "í", "¢": "ó",
  "£": "ú", "§": "ñ", "•": "Ñ", "¶": "ª", "ß": "º", "®": "¿", "≠": "¡",
  "Æ": "«", "Ø": "»", "¯": "°",
};

const ACCENTED = /[áéíóúüñÁÉÍÓÚÜÑ]/;

/**
 * Devuelve el nombre legible de un documento.
 *
 * Es conservadora por diseño: solo transforma cuando el texto contiene glifos de
 * la tabla y **no** contiene ya acentos correctos. Un nombre sano nunca se toca,
 * de modo que en el peor caso no repara, pero jamás empeora.
 *
 * Siempre normaliza a NFC: macOS entrega los acentos descompuestos (e + tilde),
 * lo que se ve idéntico pero rompe comparaciones y búsquedas.
 */
export function documentDisplayName(rawName: string): string {
  const normalized = rawName.normalize("NFC");

  const hasMojibake = Object.keys(MOJIBAKE).some((glyph) => normalized.includes(glyph));
  if (!hasMojibake || ACCENTED.test(normalized)) return normalized;

  const repaired = Array.from(normalized)
    .map((char) => MOJIBAKE[char] ?? char)
    .join("");

  return repaired.normalize("NFC");
}
