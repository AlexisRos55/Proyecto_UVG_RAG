import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/shared/lib/api-client";

/**
 * Reintentar solo cuando puede servir de algo. Una sesión vencida o un permiso
 * denegado no mejoran por insistir: reintentarlos retrasa el mensaje que el
 * usuario necesita ver.
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && !error.isRetryable) return false;
  return failureCount < 2;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetry,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
