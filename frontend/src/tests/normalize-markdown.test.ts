import { describe, expect, it } from "vitest";

import { markdownToPlainText, normalizeMarkdown } from "@/features/chat/lib/normalize-markdown";

describe("normalizeMarkdown", () => {
  it("convierte viñetas tipográficas en lista Markdown real", () => {
    // Caso capturado en producción: el modelo emitía «•» y cada elemento quedaba
    // como párrafo suelto en vez de lista.
    const crudo = "Se ofrecen:\n\n• **Beca de Excelencia**: cubre 50%.\n\n• **Beca Deportiva**: cubre 30%.";
    const salida = normalizeMarkdown(crudo);
    expect(salida).toContain("- **Beca de Excelencia**");
    expect(salida).toContain("- **Beca Deportiva**");
    expect(salida).not.toContain("•");
  });

  it("normaliza listas numeradas con paréntesis", () => {
    expect(normalizeMarkdown("1) Primero\n2) Segundo")).toBe("1. Primero\n2. Segundo");
  });

  it("separa una lista pegada al párrafo anterior", () => {
    expect(normalizeMarkdown("Requisitos:\n- Uno\n- Dos")).toBe("Requisitos:\n\n- Uno\n- Dos");
  });

  it("corrige encabezados sin espacio", () => {
    expect(normalizeMarkdown("##Comparación")).toBe("## Comparación");
  });

  it("colapsa saltos de línea excesivos", () => {
    expect(normalizeMarkdown("Uno\n\n\n\nDos")).toBe("Uno\n\nDos");
  });

  it("no altera Markdown que ya es válido", () => {
    const valido = "## Título\n\n- Uno\n- Dos\n\nTexto **en negrita**.";
    expect(normalizeMarkdown(valido)).toBe(valido);
  });
});

describe("markdownToPlainText", () => {
  it("quita la sintaxis para que el texto se pueda pegar en un correo", () => {
    const salida = markdownToPlainText("## Becas\n\n- **Excelencia**: cubre el _50%_.");
    expect(salida).toBe("Becas\n\n• Excelencia: cubre el 50%.");
  });

  it("aplana una tabla en filas legibles", () => {
    const tabla = "| Criterio | Valor |\n|---|---|\n| Cobertura | 50% |";
    const salida = markdownToPlainText(tabla);
    expect(salida).toContain("Criterio · Valor");
    expect(salida).toContain("Cobertura · 50%");
    expect(salida).not.toContain("|");
  });

  it("conserva el texto de los enlaces y descarta la URL", () => {
    expect(markdownToPlainText("Ver el [reglamento](https://uvg.edu.gt/x).")).toBe(
      "Ver el reglamento.",
    );
  });

  it("no rompe palabras con guion bajo interno", () => {
    expect(markdownToPlainText("El archivo becas_y_beneficios.pdf")).toBe(
      "El archivo becas_y_beneficios.pdf",
    );
  });
});
