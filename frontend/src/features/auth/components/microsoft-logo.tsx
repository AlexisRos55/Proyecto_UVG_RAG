import type { SVGProps } from "react";

/**
 * Logotipo oficial de Microsoft (cuatro cuadrantes). Se dibuja en línea en lugar de
 * cargarse como imagen para que herede el tamaño del botón y no dependa de un recurso
 * externo; los colores son los de la marca y no deben tematizarse.
 */
export function MicrosoftLogo(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 23 23" role="img" aria-hidden="true" focusable="false" {...props}>
      <rect x="1" y="1" width="10" height="10" fill="#F25022" />
      <rect x="12" y="1" width="10" height="10" fill="#7FBA00" />
      <rect x="1" y="12" width="10" height="10" fill="#00A4EF" />
      <rect x="12" y="12" width="10" height="10" fill="#FFB900" />
    </svg>
  );
}
