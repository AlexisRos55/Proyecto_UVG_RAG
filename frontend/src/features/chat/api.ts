import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/auth-context";
import { apiClient } from "@/shared/lib/api-client";
import type { AnswerResponse, ConversationDto } from "@/shared/types/api";

const HISTORY_QUERY_KEY = ["chat", "history"];

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
