import { useMemo, useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/features/auth/auth-context";
import { useAskQuestion, useChatHistory } from "@/features/chat/api";
import { MessageInput } from "@/features/chat/components/message-input";
import { MessageList } from "@/features/chat/components/message-list";
import { Sidebar } from "@/features/chat/components/sidebar";
import { ApiError } from "@/shared/lib/api-client";

const TITLE_MAX_LENGTH = 42;

export function ChatPage() {
  const { session, logout } = useAuth();
  const { data: conversations, isLoading } = useChatHistory();
  const askQuestion = useAskQuestion();
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  // "Nueva conversación" (sprint 1, ADR-0011): reinicio visual local. El backend conserva
  // una única conversación activa por estudiante (FR-14); el historial multi-hilo persistente
  // queda para un sprint futuro.
  const [clearedAt, setClearedAt] = useState<string | null>(null);

  const messages = useMemo(() => {
    const allMessages = conversations?.[0]?.messages ?? [];
    return clearedAt ? allMessages.filter((m) => m.created_at > clearedAt) : allMessages;
  }, [conversations, clearedAt]);

  const conversationTitle = useMemo(() => {
    const firstQuestion = messages.find((m) => m.role === "student");
    if (!firstQuestion) return null;
    return firstQuestion.content.length > TITLE_MAX_LENGTH
      ? `${firstQuestion.content.slice(0, TITLE_MAX_LENGTH)}…`
      : firstQuestion.content;
  }, [messages]);

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

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        userEmail={session?.email ?? ""}
        conversationTitle={conversationTitle}
        onNewChat={() => setClearedAt(new Date().toISOString())}
        onLogout={logout}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-muted/40">
        <header className="flex items-center gap-3 border-b bg-background px-6 py-3.5">
          <img src="/brand/logo-uvg-altiplano.png" alt="" className="size-7 rounded-md" />
          <div className="leading-tight">
            <p className="text-sm font-semibold text-foreground">Asistente Virtual Institucional</p>
            <p className="text-xs text-muted-foreground">
              Responde con base en documentos oficiales de UVG Altiplano
            </p>
          </div>
        </header>

        {isLoading ? (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            Cargando conversación…
          </div>
        ) : (
          <MessageList
            messages={messages}
            pendingQuestion={pendingQuestion}
            isAnswering={askQuestion.isPending}
            onSuggestionSelect={handleSend}
          />
        )}

        <MessageInput disabled={askQuestion.isPending} onSend={handleSend} />
      </div>
    </div>
  );
}
