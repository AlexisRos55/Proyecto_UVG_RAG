import { useMemo, useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/features/auth/auth-context";
import { isBackendOnline, useAskQuestion, useBackendStatus, useChatHistory } from "@/features/chat/api";
import { ChatHeader } from "@/features/chat/components/chat-header";
import { Composer } from "@/features/chat/components/composer";
import { EmptyState } from "@/features/chat/components/empty-state";
import { MessageThread } from "@/features/chat/components/message-thread";
import { Sidebar, type ConversationListItem } from "@/features/chat/components/sidebar";
import { displayNameFromEmail, generateConversationTitle } from "@/features/chat/lib/format";
import { ApiError } from "@/shared/lib/api-client";

export function ChatPage() {
  const { session, logout } = useAuth();
  const { data: conversations, isLoading } = useChatHistory();
  const { data: healthStatus, isError: healthIsError } = useBackendStatus();
  const askQuestion = useAskQuestion();
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  // "Nueva conversación" (sprint 1, ADR-0011): reinicio visual local. El backend conserva
  // una única conversación activa por estudiante (FR-14); el historial multi-hilo persistente
  // queda para un sprint futuro — ver docs/07-backlog.md.
  const [clearedAt, setClearedAt] = useState<string | null>(null);

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
        conversations={sidebarConversations}
        activeConversationId={activeConversation?.id ?? null}
        onSelectConversation={() => setClearedAt(null)}
        onNewChat={() => {
          setClearedAt(new Date().toISOString());
          setIsSidebarOpen(false);
        }}
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
            <p className="text-ui text-muted-foreground pt-24 text-center">Cargando conversación…</p>
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
