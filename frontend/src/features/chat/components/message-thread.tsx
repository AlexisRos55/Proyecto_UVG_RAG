import { useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";

import { AnswerBlock, QuestionBlock } from "@/features/chat/components/message-turn";
import { ThinkingIndicator } from "@/features/chat/components/thinking-indicator";
import type { MessageDto } from "@/shared/types/api";

interface MessageThreadProps {
  messages: MessageDto[];
  pendingQuestion: string | null;
  isAnswering: boolean;
}

export function MessageThread({ messages, pendingQuestion, isAnswering }: MessageThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pendingQuestion, isAnswering]);

  return (
    <div className="mx-auto w-full max-w-[var(--measure)] px-6 pt-10 pb-16 sm:px-8">
      {messages.map((message, index) =>
        message.role === "student" ? (
          <QuestionBlock key={message.id} content={message.content} isFirst={index === 0} />
        ) : (
          <AnswerBlock key={message.id} message={message} />
        ),
      )}

      {pendingQuestion && (
        <QuestionBlock content={pendingQuestion} isFirst={messages.length === 0} />
      )}

      <AnimatePresence>{isAnswering && <ThinkingIndicator />}</AnimatePresence>

      <div ref={bottomRef} />
    </div>
  );
}
