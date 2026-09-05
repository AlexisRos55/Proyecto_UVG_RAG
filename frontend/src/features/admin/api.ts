import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/auth-context";
import { apiClient } from "@/shared/lib/api-client";
import type { DocumentSummary, IngestResult } from "@/shared/types/api";

const DOCUMENTS_QUERY_KEY = ["admin", "documents"];

export function useDocuments() {
  const { session } = useAuth();
  return useQuery({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: () => apiClient.get<DocumentSummary[]>("/admin/documents", session?.token),
    enabled: Boolean(session),
  });
}

export function useUploadDocument() {
  const { session } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiClient.postForm<IngestResult>("/admin/documents", formData, session?.token);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });
}

export function useDeleteDocument() {
  const { session } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      apiClient.delete<void>(`/admin/documents/${documentId}`, session?.token),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });
}

export function useReindexDocument() {
  const { session } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      apiClient.post<IngestResult>(`/admin/documents/${documentId}/reindex`, undefined, session?.token),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });
}
