import { useState, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface MessageInputProps {
  disabled: boolean;
  onSend: (question: string) => void;
}

export function MessageInput({ disabled, onSend }: MessageInputProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t bg-background px-4 py-4">
      <div className="mx-auto flex w-full max-w-3xl items-end gap-2 rounded-2xl border bg-card p-2 shadow-sm">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Pregunta sobre reglamentos, becas o seguros de UVG Altiplano…"
          rows={1}
          disabled={disabled}
          className="max-h-40 min-h-9 resize-none border-none bg-transparent shadow-none focus-visible:ring-0"
        />
        <Button
          onClick={submit}
          disabled={disabled || value.trim().length === 0}
          size="icon"
          className="shrink-0 rounded-full"
          aria-label="Enviar pregunta"
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-muted-foreground">
        El asistente responde únicamente con base en documentos oficiales indexados y puede
        no tener información sobre todos los temas.
      </p>
    </div>
  );
}
