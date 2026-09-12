import "@testing-library/jest-dom/vitest";

if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverPolyfill {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverPolyfill as unknown as typeof ResizeObserver;
}

// Framer Motion mide keyframes leyendo el scroll de la ventana; jsdom no implementa
// window.scrollTo y lanza un error ruidoso (no una falla) en cada animación de altura.
if (typeof window !== "undefined") {
  window.scrollTo = () => {};
}
