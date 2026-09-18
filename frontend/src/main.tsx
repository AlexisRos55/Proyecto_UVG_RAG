import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";

import { App } from "@/app/App";
import { AuthProvider } from "@/features/auth/auth-context";
import { queryClient } from "@/shared/lib/query-client";

import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
          {/* Abajo al centro: la confirmación aparece cerca del compositor y de los
              controles de la lista, que es donde el usuario está mirando cuando
              actúa. En la esquina superior derecha pasaba desapercibida. */}
          <Toaster
            richColors
            position="bottom-center"
            closeButton
            toastOptions={{ duration: 4500 }}
          />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
