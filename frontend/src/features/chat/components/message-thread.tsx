import { AnimatePresence } from "framer-motion";

import { AnswerBlock, QuestionBlock } from "@/features/chat/components/message-turn";
import { ThinkingIndicator } from "@/features/chat/components/thinking-indicator";
import type { MessageDto } from "@/shared/types/api";

interface MessageThreadProps {
  messages: MessageDto[];
  pendingQuestion: string | null;
  isAnswering: boolean;
}

/**
 * Un turno es "social" cuando su respuesta no es una afirmación sobre la
 * normativa: saludos, agradecimientos, preguntas sobre el propio asistente.
 *
 * La señal ya viaja en los datos —una habilidad local devuelve `is_grounded`
 * nulo— así que no hace falta clasificar de nuevo en la interfaz. Estos turnos
 * se componen compactos: el ritmo amplio está pensado para lectura larga y con
 * un «hola» dejaba media pantalla vacía.
 */
function isSocialTurn(reply: MessageDto | undefined): boolean {
  return reply?.role === "assistant" && reply.is_grounded === null;
}

/**
 * El hilo ya no gestiona su propio desplazamiento.
 *
 * Antes llamaba a `scrollIntoView` sobre un centinela cada vez que cambiaba el
 * número de mensajes, lo que animaba un viaje hasta el final al abrir la
 * aplicación y te devolvía abajo si habías subido a releer. Esa política vive
 * ahora en `useThreadScroll`, junto al contenedor que de verdad hace scroll.
 */
export function MessageThread({ messages, pendingQuestion, isAnswering }: MessageThreadProps) {
  return (
    <div className="mx-auto w-full max-w-[var(--measure)] px-6 pt-10 pb-16 sm:px-8">
      {messages.map((message, index) => {
        const compact = isSocialTurn(
          message.role === "student" ? messages[index + 1] : messages[index],
        );

        return message.role === "student" ? (
          <QuestionBlock
            key={message.id}
            content={message.content}
            isFirst={index === 0}
            compact={compact}
          />
        ) : (
          <AnswerBlock key={message.id} message={message} compact={compact} />
        );
      })}

      {pendingQuestion && (
        // Todavía no se sabe si será social: se compone como consulta, que es el
        // caso mayoritario y el que el usuario espera ver encabezado.
        <QuestionBlock content={pendingQuestion} isFirst={messages.length === 0} compact={false} />
      )}

      <AnimatePresence>{isAnswering && <ThinkingIndicator />}</AnimatePresence>
    </div>
  );
}
