import { describe, expect, it } from "vitest";

import { generateConversationTitle, pickTitleSource } from "@/features/chat/lib/format";

type Msg = { role: string; content: string; is_grounded: boolean | null };

const student = (content: string): Msg => ({ role: "student", content, is_grounded: null });
const social = (): Msg => ({ role: "assistant", content: "Hola.", is_grounded: null });
const grounded = (): Msg => ({ role: "assistant", content: "…", is_grounded: true });
const abstained = (): Msg => ({ role: "assistant", content: "…", is_grounded: false });

describe("pickTitleSource", () => {
  it("ignora los saludos", () => {
    expect(
      pickTitleSource([student("Hola"), social(), student("¿Qué becas hay?"), grounded()]),
    ).toBe("¿Qué becas hay?");
  });

  it("prefiere una consulta respondida antes que una abstención previa", () => {
    // El caso real que lo motivó: un texto sin sentido recibió abstención y
    // titulaba el hilo por ser el primero.
    expect(
      pickTitleSource([
        student("xk29 qzwoe plmn"),
        abstained(),
        student("¿Qué cubre el seguro estudiantil?"),
        grounded(),
      ]),
    ).toBe("¿Qué cubre el seguro estudiantil?");
  });

  it("acepta una abstención si no hay ninguna consulta respondida", () => {
    expect(pickTitleSource([student("¿Hay parqueo para bicicletas?"), abstained()])).toBe(
      "¿Hay parqueo para bicicletas?",
    );
  });

  it("devuelve null cuando sólo hay conversación social", () => {
    expect(pickTitleSource([student("Hola"), social(), student("gracias"), social()])).toBeNull();
  });

  it("devuelve null cuando la pregunta aún no tiene respuesta", () => {
    expect(pickTitleSource([student("¿Qué becas hay?")])).toBeNull();
  });
});

describe("generateConversationTitle", () => {
  it("no parte una palabra por la mitad", () => {
    const title = generateConversationTitle(
      "¿Qué becas ofrece la universidad y qué requisitos tienen?",
    );
    expect(title.endsWith("…")).toBe(true);
    expect(title.length).toBeLessThanOrEqual(39);
    expect(title).not.toMatch(/\s…$/);
  });

  it("deja intacto un título corto", () => {
    expect(generateConversationTitle("¿Qué becas hay?")).toBe("¿Qué becas hay?");
  });
});
