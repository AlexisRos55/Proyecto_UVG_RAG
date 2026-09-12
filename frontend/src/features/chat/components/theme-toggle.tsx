import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";

import { IconButton } from "@/design-system/icon-button";

export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  // Evita el parpadeo/discrepancia de hidratación: hasta que el cliente monte, next-themes
  // no sabe todavía si el sistema prefiere claro u oscuro.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return <div className="size-7" aria-hidden="true" />;

  const isDark = resolvedTheme === "dark";

  return (
    <IconButton
      size="sm"
      label={isDark ? "Modo claro" : "Modo oscuro"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={className}
    >
      {isDark ? (
        <Sun className="size-4" strokeWidth={1.75} />
      ) : (
        <Moon className="size-4" strokeWidth={1.75} />
      )}
    </IconButton>
  );
}
