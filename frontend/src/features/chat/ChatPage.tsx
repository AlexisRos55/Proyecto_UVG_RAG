import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/design-system/states";
import { useAuth } from "@/features/auth/auth-context";
import {
  isBackendOnline,
  useAskQuestion,
  useBackendStatus,
  useChatHistory,
} from "@/features/chat/api";
import { ChatHeader } from "@/features/chat/components/chat-header";
import { Composer } from "@/features/chat/components/composer";
import { ConnectionNotice } from "@/features/chat/components/connection-notice";
import { EmptyState } from "@/features/chat/components/empty-state";
import { MessageThread } from "@/features/chat/components/message-thread";
import { ScrollToBottom } from "@/features/chat/components/scroll-to-bottom";
import { Sidebar, type ConversationListItem } from "@/features/chat/components/sidebar";
import { ThreadSkeleton } from "@/features/chat/components/thread-skeleton";
import { useThreadScroll } from "@/features/chat/hooks/use-thread-scroll";
import {
  displayNameFromEmail,
  generateConversationTitle,
  pickTitleSource,
} from "@/features/chat/lib/format";
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

  const isOffline = !isBackendOnline(healthStatus, healthIsError);

  const closeSidebar = useCallback(() => setIsSidebarOpen(false), []);
  const openSidebar = useCallback(() => setIsSidebarOpen(true), []);

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

  // El título sale de la primera consulta real, nunca de un saludo: antes una
  // conversación que empezaba con «Hola» se llamaba así para siempre.
  const conversationTitle = useMemo(() => {
    const source = pickTitleSource(messages);
    return source ? generateConversationTitle(source) : null;
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

  // El desplazamiento se ancla al contenedor real, y reacciona a lo que hace
  // crecer el hilo: mensajes nuevos, la pregunta en vuelo y el indicador.
  const { containerRef, isAtBottom, scrollToBottom } = useThreadScroll([
    messages.length,
    pendingQuestion,
    askQuestion.isPending,
  ]);

  /**
   * Devuelve si la consulta se envió. El compositor usa esa respuesta para
   * recuperar el texto cuando falla: antes lo vaciaba siempre, así que una
   * caída del servidor borraba la pregunta recién escrita sin rastro.
   */
  const handleSend = useCallback(
    async (question: string): Promise<boolean> => {
      setPendingQuestion(question);
      try {
        await askQuestion.mutateAsync(question);
        return true;
      } catch (sendError: unknown) {
        const message =
          sendError instanceof ApiError ? sendError.message : "No se pudo enviar la pregunta.";
        toast.error(message);
        return false;
      } finally {
        setPendingQuestion(null);
      }
    },
    [askQuestion],
  );

  const isEmpty = messages.length === 0 && !pendingQuestion;

  return (
    <div className="bg-background flex h-dvh overflow-hidden">
      {/* Salto al contenido: el panel lateral tiene una docena de controles antes
          de la conversación, y sin este enlace quien navega con teclado los
          recorre todos en cada visita. */}
      <a
        href="#conversacion"
        className="bg-surface-raised text-ui shadow-float focus:ring-ring sr-only font-medium focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-[60] focus:rounded-lg focus:px-3.5 focus:py-2 focus:ring-2 focus:outline-none"
      >
        Saltar a la conversación
      </a>

      <Sidebar
        userEmail={session?.email ?? ""}
        isAdmin={isAdmin}
        conversations={sidebarConversations}
        activeConversationId={activeConversation?.id ?? null}
        onSelectConversation={closeSidebar}
        onNewChat={startNewConversation}
        onLogout={logout}
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
      />

      <main className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        <ChatHeader
          title={conversationTitle}
          isOnline={!isOffline}
          onOpenSidebar={openSidebar}
        />

        {/* El contenido pasa por debajo de la cabecera translúcida: de ahí el
            padding superior en lugar de un header que ocupe su propia fila. */}
        <div
          ref={containerRef}
          id="conversacion"
          className="min-h-0 flex-1 overflow-y-auto pt-[var(--header-height)]"
          tabIndex={-1}
        >
          {isLoading ? (
            <ThreadSkeleton />
          ) : isError ? (
            /* Un fallo al cargar el historial ya no se disfraza de "eres nuevo":
               se explica y se ofrece reintentar. */
            <div className="px-6 pt-20">
              <ErrorState error={error} onRetry={() => void refetch()} />
            </div>
          ) : isEmpty ? (
            <EmptyState
              userName={displayNameFromEmail(session?.email ?? "")}
              onSelect={(question) => void handleSend(question)}
            />
          ) : (
            <MessageThread
              messages={messages}
              pendingQuestion={pendingQuestion}
              isAnswering={askQuestion.isPending}
            />
          )}
        </div>

        {/* Sólo cuando hay hilo del que alejarse. */}
        <ScrollToBottom show={!isEmpty && !isAtBottom} onClick={() => scrollToBottom("smooth")} />

        {/* El aviso vive junto al compositor, no dentro del hilo. Colocado arriba
            del área con scroll quedaba fuera de vista en cuanto la conversación
            crecía: había que subir miles de píxeles para enterarse de que el
            servidor estaba caído. Aquí está siempre visible y justo al lado del
            campo que explica por qué está deshabilitado. */}
        <ConnectionNotice isOffline={isOffline} />

        <Composer isSending={askQuestion.isPending} isOffline={isOffline} onSend={handleSend} />
      </main>
    </div>
  );
}
