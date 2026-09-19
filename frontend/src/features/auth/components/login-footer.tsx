const APP_VERSION = "v1.0";

/** Pie del portal: versión del sistema y procedencia académica del proyecto. */
export function LoginFooter() {
  return (
    <footer className="flex flex-wrap items-center justify-center gap-x-2.5 gap-y-1 text-center text-caption text-text-tertiary">
      <span className="rounded-md bg-muted px-1.5 py-0.5 font-medium text-muted-foreground tabular-nums">
        {APP_VERSION}
      </span>
      <span aria-hidden="true" className="hidden sm:inline">
        ·
      </span>
      <span>Proyecto de Graduación 2026</span>
    </footer>
  );
}
