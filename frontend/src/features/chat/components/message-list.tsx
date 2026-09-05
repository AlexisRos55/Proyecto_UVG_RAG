import { useEffect, useRef } from "react";
import { BookOpen, FileText, GraduationCap, ShieldCheck, Sparkles } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "@/features/chat/components/message-bubble";
import type { MessageDto } from "@/shared/types/api";

interface MessageListProps {
  messages: MessageDto[];
  pendingQuestion: string | null;
  isAnswering: boolean;
  onSuggestionSelect: (question: string) => void;
}

const SUGGESTIONS = [
  {
    icon: BookOpen,
    label: "Reglamentos y normativas",
    question: "¿Cuáles son las normas del reglamento estudiantil que debo conocer?",
  },
  {
    icon: GraduationCap,
    label: "Becas y beneficios",
    question: "¿Qué becas y beneficios ofrece la universidad?",
  },
  {
    icon: ShieldCheck,
    label: "Seguro estudiantil",
    question: "¿Qué cubre el seguro estudiantil?",
  },
  {
    icon: FileText,
    label: "Trámites y procedimientos",
    question: "¿Qué trámites y procedimientos debo conocer como estudiante?",
  },
] as const;

export function MessageList({
  messages,
  pendingQuestion,
  isAnswering,
  onSuggestionSelect,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, pendingQuestion, isAnswering]);

  const isEmpty = messages.length === 0 && !pendingQuestion;

  return (
    <ScrollArea className="min-h-0 flex-1 px-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-5 py-8">
        {isEmpty && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
              <Sparkles className="size-6" />
            </div>
            <h2 className="text-lg font-semibold">¿En qué puedo ayudarte?</h2>
            <p className="max-w-sm text-sm text-muted-foreground">
              Pregúntame sobre reglamentos, becas o seguros de UVG Altiplano. Responderé
              únicamente con base en los documentos oficiales indexados.
            </p>

            <div className="mt-4 grid w-full max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
              {SUGGESTIONS.map(({ icon: Icon, label, question }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => onSuggestionSelect(question)}
                  className="flex items-start gap-3 rounded-xl border bg-card p-3.5 text-left shadow-sm transition-colors hover:border-primary/30 hover:bg-accent"
                >
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent text-primary">
                    <Icon className="size-4" />
                  </div>
                  <div className="leading-tight">
                    <p className="text-sm font-medium text-foreground">{label}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{question}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {pendingQuestion && (
          <MessageBubble
            message={{
              role: "student",
              content: pendingQuestion,
              is_grounded: null,
              confidence: null,
              sources: [],
            }}
          />
        )}

        {isAnswering && (
          <div className="flex items-center gap-3">
            <Avatar size="sm">
              <AvatarFallback className="bg-primary text-primary-foreground">
                <Sparkles className="size-3.5" />
              </AvatarFallback>
            </Avatar>
            <div className="flex items-center gap-1 rounded-2xl border bg-card px-4 py-3">
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
