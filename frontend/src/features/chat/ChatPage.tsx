import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/design-system/states";
import { useAuth } from "@/features/auth/auth-context";
import { isBackendOnline, useAskQuestion, useBackendStatus, useChatHistory } from "@/features/chat/api";
import { ChatHeader } from "@/features/chat/components/chat-header";
import { Composer } from "@/features/chat/components/composer";
import { EmptyState } from "@/features/chat/components/empty-state";
import { MessageThread } from "@/features/chat/components/message-thread";
import { Sidebar, type ConversationListItem } from "@/features/chat/components/sidebar";
import { displayNameFromEmail, generateConversationTitle } from "@/features/chat/lib/format";
import { ApiError } from "@/shared/lib/api-client";

/**
 * "Nueva conversación" (sprint 1, ADR-0011): reinicio local. El backend conserva una
 * única conversación activa por estudiante (FR-14), así que el corte se marca en el
 * cliente — pero se **persiste** por usuario. Antes vivía solo en memoria: el usuario
 * creía haber empezado de cero, recargaba y la conversación "borrada" reaparecía
 * completa. El historial multi-hilo real queda para un sprint futuro (docs/07-backlog.md).
 */
const CLEARED_AT_KEY = "asistente-rag.cleared-at";

function readClearedAt(userId: string | undefined): string | null {
  if (!userId) return null;
  try {
    return localStorage.getItem(`${CLEARED_AT_KEY}.${userId}`);
  } catch {
    return null;
  }
}

export function ChatPage() {
  const { session, logout, isAdmin } = useAuth();
  const { data: conversations, isLoading, isError, error, refetch } = useChatHistory();
  const { data: healthStatus, isError: healthIsError } = useBackendStatus();
  const askQuestion = useAskQuestion();
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [clearedAt, setClearedAt] = useState<string | null>(() => readClearedAt(session?.userId));

  const startNewConversation = useCallback(() => {
    const now = new Date().toISOString();
    setClearedAt(now);
    setIsSidebarOpen(false);
    if (!session?.userId) return;
    try {
      localStorage.setItem(`${CLEARED_AT_KEY}.${session.userId}`, now);
    } catch {
      // Sin almacenamiento el corte dura lo que la pestaña; no es motivo de error.
    }
  }, [session?.userId]);

  const activeConversation = conversations?.[0] ?? null;

  const messages = useMemo(() => {
    const allMessages = activeConversation?.messages ?? [];
    return clearedAt ? allMessages.filter((m) => m.created_at > clearedAt) : allMessages;
  }, [activeConversation, clearedAt]);

  const conversationTitle = useMemo(() => {
    const firstQuestion = messages.find((m) => m.role === "student");
    return firstQuestion ? generateConversationTitle(firstQuestion.content) : null;
  }, [messages]);

  const sidebarConversations: ConversationListItem[] = useMemo(() => {
    if (!activeConversation || !conversationTitle) return [];
    const lastMessage = messages.at(-1);
    return [
      {
        id: activeConversation.id,
        title: conversationTitle,
        updatedAt: lastMessage?.created_at ?? activeConversation.created_at,
      },
    ];
  }, [activeConversation, conversationTitle, messages]);

  const handleSend = (question: string) => {
    setPendingQuestion(question);
    askQuestion.mutate(question, {
      onSettled: () => setPendingQuestion(null),
      onError: (error: unknown) => {
        const message = error instanceof ApiError ? error.message : "No se pudo enviar la pregunta.";
        toast.error(message);
      },
    });
  };

  const isEmpty = messages.length === 0 && !pendingQuestion;

  return (
    <div className="bg-background flex h-dvh overflow-hidden">
      <Sidebar
        userEmail={session?.email ?? ""}
        isAdmin={isAdmin}
        conversations={sidebarConversations}
        activeConversationId={activeConversation?.id ?? null}
        onSelectConversation={() => setIsSidebarOpen(false)}
        onNewChat={startNewConversation}
        onLogout={logout}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <main className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        <ChatHeader
          title={conversationTitle}
          isOnline={isBackendOnline(healthStatus, healthIsError)}
          onOpenSidebar={() => setIsSidebarOpen(true)}
        />

        {/* El contenido pasa por debajo de la cabecera translúcida: de ahí el
            padding superior en lugar de un header que ocupe su propia fila. */}
        <div className="min-h-0 flex-1 overflow-y-auto pt-[var(--header-height)]">
          {isLoading ? (
            <p className="text-ui text-muted-foreground pt-24 text-center" role="status">
              Cargando conversación…
            </p>
          ) : isError ? (
            /* Un fallo al cargar el historial ya no se disfraza de "eres nuevo":
               se explica y se ofrece reintentar. */
            <div className="px-6 pt-20">
              <ErrorState error={error} onRetry={() => void refetch()} />
            </div>
          ) : isEmpty ? (
            <EmptyState
              userName={displayNameFromEmail(session?.email ?? "")}
              onSelect={handleSend}
            />
          ) : (
            <MessageThread
              messages={messages}
              pendingQuestion={pendingQuestion}
              isAnswering={askQuestion.isPending}
            />
          )}
        </div>

        <Composer disabled={askQuestion.isPending} onSend={handleSend} />
      </main>
    </div>
  );
}
