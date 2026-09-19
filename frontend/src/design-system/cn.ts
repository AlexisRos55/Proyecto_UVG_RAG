import { createCn } from "cn/config";

/**
 * `cn` configurado con la escala tipográfica propia del design system.
 *
 * Sin esta configuración, `cn("text-title text-foreground")` devolvía
 * `"text-foreground"`: el algoritmo de fusión resuelve conflictos por grupo de
 * utilidad y, al no conocer `text-title`, lo clasificaba como color de texto —
 * el mismo grupo que `text-foreground`— y descartaba el primero por ser el
 * anterior. El resultado es que toda la jerarquía tipográfica desaparecía en
 * silencio allí donde un componente combinaba tamaño y color, y el texto caía
 * al 16px/400 que trae el navegador.
 *
 * Declarar los tokens en el grupo `font-size` restablece el criterio correcto:
 * un tamaño sólo entra en conflicto con otro tamaño.
 */
export const cn = createCn({
  extend: {
    classGroups: {
      "font-size": [{ text: ["display", "title", "heading", "body", "ui", "caption", "micro"] }],
    },
  },
});
