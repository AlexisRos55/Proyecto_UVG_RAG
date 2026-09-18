import { describe, expect, it } from "vitest";

import { documentDisplayName } from "@/shared/lib/document-name";

describe("documentDisplayName", () => {
  // Nombres reales del corpus institucional, tomados de la base de datos.
  it.each([
    ["Educaci¢n F°sica 2025 UVGA.pdf", "Educación Física 2025 UVGA.pdf"],
    ["Maestr°a 2025.pdf", "Maestría 2025.pdf"],
    ["Inform†tica 2025.pdf", "Informática 2025.pdf"],
    ["Administraci¢n de Empresas 2025.pdf", "Administración de Empresas 2025.pdf"],
    ["Agr°cola y Pecuaria 2025.pdf", "Agrícola y Pecuaria 2025.pdf"],
    ["Industrializaci¢n de Alimentos 2025 f.pdf", "Industrialización de Alimentos 2025 f.pdf"],
  ])("repara %s", (corrupto, esperado) => {
    expect(documentDisplayName(corrupto)).toBe(esperado);
  });

  it("no altera un nombre que ya está bien escrito", () => {
    const sano = "Proceso de Admisión e Inscripción Estudiante de Primer Ingreso.pdf";
    expect(documentDisplayName(sano)).toBe(sano);
  });

  it("no altera un nombre sin caracteres especiales", () => {
    expect(documentDisplayName("becas_y_beneficios.pdf")).toBe("becas_y_beneficios.pdf");
  });

  it("normaliza acentos descompuestos de macOS a su forma compuesta", () => {
    const descompuesto = "Calendario Académico V3.pdf"; // e + tilde combinante
    expect(documentDisplayName(descompuesto)).toBe("Calendario Académico V3.pdf");
  });

  it("deja intacto un nombre con acentos correctos aunque contenga un símbolo de la tabla", () => {
    // Guarda contra falsos positivos: si ya hay acentos correctos, no se toca.
    const mixto = "Informe 90° de Admisión.pdf";
    expect(documentDisplayName(mixto)).toBe(mixto);
  });
});
