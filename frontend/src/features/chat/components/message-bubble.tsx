import { cn } from "cn";
import { FileText, Sparkles, User } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import type { MessageDto } from "@/shared/types/api";

interface MessageBubbleProps {
  message: Pick<MessageDto, "role" | "content" | "is_grounded" | "confidence" | "sources">;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isStudent = message.role === "student";

  return (
    <div className={cn("flex w-full items-start gap-3", isStudent && "flex-row-reverse")}>
      <Avatar size="sm" className="mt-0.5">
        <AvatarFallback className={isStudent ? "bg-primary/10 text-primary" : "bg-primary text-primary-foreground"}>
          {isStudent ? <User className="size-3.5" /> : <Sparkles className="size-3.5" />}
        </AvatarFallback>
      </Avatar>

      <div className={cn("flex max-w-[75%] flex-col gap-2", isStudent && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm",
            isStudent
              ? "bg-primary text-primary-foreground"
              : "border bg-card text-card-foreground",
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {!isStudent && message.is_grounded !== null && (
          <div className="flex flex-wrap items-center gap-1.5">
            {message.is_grounded ? (
              message.sources.length > 0 ? (
                message.sources.map((source) => (
                  <Badge key={source.document_name} variant="secondary" className="gap-1">
                    <FileText className="size-3" />
                    Fuente: {source.document_name}
                    {source.page_number != null ? ` (pág. ${source.page_number})` : ""}
                  </Badge>
                ))
              ) : (
                <Badge variant="secondary">Fundamentado en documentos oficiales</Badge>
              )
            ) : (
              <Badge variant="destructive">Sin información suficiente en los documentos oficiales</Badge>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
