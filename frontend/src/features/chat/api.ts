import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/auth-context";
import { apiClient } from "@/shared/lib/api-client";
import type { AnswerResponse, ConversationDto } from "@/shared/types/api";

const HISTORY_QUERY_KEY = ["chat", "history"];

/** Estado real del backend (no un indicador decorativo): sondea GET /health, el mismo
 * endpoint que usa el healthcheck de Docker — no introduce ninguna ruta nueva. */
export function useBackendStatus() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get<{ status: string }>("/health"),
    refetchInterval: 30_000,
    retry: false,
    // Un error de red no debe verse como "cargando" indefinidamente: se resuelve a
    // "desconectado" tan pronto como sea posible.
    throwOnError: () => false,
  });
}

export function isBackendOnline(
  status: { status: string } | undefined,
  isError: boolean,
): boolean {
  return !isError && status?.status === "ok";
}

export function useChatHistory() {
  const { session } = useAuth();
  return useQuery({
    queryKey: HISTORY_QUERY_KEY,
    queryFn: () => apiClient.get<ConversationDto[]>("/chat/history", session?.token),
    enabled: Boolean(session),
  });
}

export function useAskQuestion() {
  const { session } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (question: string) =>
      apiClient.post<AnswerResponse>("/chat", { question }, session?.token),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: HISTORY_QUERY_KEY });
    },
  });
}
