import { describe, expect, it } from "vitest";

import { cn } from "@/design-system/cn";

/**
 * Este fallo no rompe el build ni los tipos: simplemente el texto se queda con
 * el 16px/400 del navegador y la jerarquía desaparece. Por eso se fija aquí.
 */
describe("cn con la escala tipográfica del design system", () => {
  it("conserva el tamaño cuando se combina con un color", () => {
    expect(cn("text-title text-foreground")).toBe("text-title text-foreground");
    expect(cn("text-body text-muted-foreground font-medium")).toBe(
      "text-body text-muted-foreground font-medium",
    );
    expect(cn("text-micro text-text-tertiary uppercase")).toBe(
      "text-micro text-text-tertiary uppercase",
    );
  });

  it("sigue resolviendo conflictos reales: tamaño contra tamaño, color contra color", () => {
    expect(cn("text-body text-title")).toBe("text-title");
    expect(cn("text-body text-lg")).toBe("text-lg");
    expect(cn("text-foreground text-muted-foreground")).toBe("text-muted-foreground");
  });

  it("cubre toda la escala declarada en tokens.css", () => {
    for (const size of ["display", "title", "heading", "body", "ui", "caption", "micro"]) {
      expect(cn(`text-${size} text-foreground`)).toContain(`text-${size}`);
    }
  });
});
