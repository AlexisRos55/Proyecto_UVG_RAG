import { describe, expect, it } from "vitest";
import {
  dedupeSources,
  documentKindLabel,
  documentTitle,
  sourceLocation,
  sourceTitle,
} from "@/shared/lib/document-label";

describe("documentTitle", () => {
  it.each([
    ["UVG.DAF.02.001 Reglamento ayudas financieras V 10.0  (27-5-26).pdf", "Reglamento ayudas financieras"],
    ["UVG.VE.02.001 Reglamento de grupos estudiantiles v2.pdf", "Reglamento de grupos estudiantiles"],
    ["becas_y_beneficios.pdf", "Becas y beneficios"],
    ["Calendario Académico V3.pdf", "Calendario Académico"],
    ["Maestr°a 2025.pdf", "Maestría 2025"],
    ["Proceso de Admisión e Inscripción Estudiante de Primer Ingreso.pdf", "Proceso de Admisión e Inscripción Estudiante de Primer Ingreso"],
  ])("limpia %s", (crudo, esperado) => {
    expect(documentTitle(crudo)).toBe(esperado);
  });
});

describe("documentKindLabel", () => {
  it.each([
    ["UVG.DAF.02.001 Reglamento ayudas financieras.pdf", "Reglamento"],
    ["Calendario Académico V3.pdf", "Calendario"],
    ["Proceso de Admisión.pdf", "Proceso"],
    ["becas_y_beneficios.pdf", "Documento oficial"],
  ])("clasifica %s", (crudo, esperado) => {
    expect(documentKindLabel(crudo)).toBe(esperado);
  });
});

describe("dedupeSources", () => {
  it("elimina duplicados reales del corpus conservando el orden", () => {
    const fuentes = [
      { document_name: "becas_y_beneficios.pdf", page_number: null },
      { document_name: "Administración de Empresas 2025.pdf", page_number: null },
      { document_name: "Administración de Empresas 2025.pdf", page_number: null },
      { document_name: "Calendario Académico V3.pdf", page_number: null },
    ];
    const salida = dedupeSources(fuentes);
    expect(salida).toHaveLength(3);
    expect(salida[0].document_name).toBe("becas_y_beneficios.pdf");
  });

  it("conserva el mismo documento si cita páginas distintas", () => {
    const fuentes = [
      { document_name: "reglamento.pdf", page_number: 3 },
      { document_name: "reglamento.pdf", page_number: 7 },
    ];
    expect(dedupeSources(fuentes)).toHaveLength(2);
  });
});

describe("citas estructuradas (ADR-0014)", () => {
  const cita = {
    document_name: "24b8330c_UVG.DAF.02.001 Reglamento ayudas financieras V 10.0.pdf",
    page_number: 10,
    page_end: 11,
    document_title: "Reglamento de ayudas financieras",
    section: "Capítulo IV · Artículo 18. Condiciones",
  };

  it("prefiere el título que declara el documento", () => {
    expect(sourceTitle(cita)).toBe("Reglamento de ayudas financieras");
    expect(sourceTitle({ document_name: "Maestr°a 2025.pdf", page_number: null })).toBe("Maestría 2025");
  });

  it("compone apartado y rango de páginas", () => {
    expect(sourceLocation(cita)).toBe("Capítulo IV · Artículo 18. Condiciones · págs. 10–11");
    expect(sourceLocation({ document_name: "x.pdf", page_number: 3 })).toBe("pág. 3");
    expect(sourceLocation({ document_name: "x.pdf", page_number: null })).toBeNull();
  });

  it("dos artículos del mismo reglamento son referencias distintas", () => {
    const otra = { ...cita, section: "Capítulo IV · Artículo 19. Penalizaciones", page_number: 11, page_end: null };
    expect(dedupeSources([cita, otra, cita])).toHaveLength(2);
  });
});
