// Tipos que reflejan los esquemas Pydantic del backend (contrato HTTP), no las entidades
// de dominio internas — ver backend/src/app/infrastructure/entrypoints/api/schemas/.

export type UserRole = "student" | "admin";

export interface AuthResponse {
  user_id: string;
  email: string;
  role: UserRole;
  session_token: string;
}

export type VerificationConfidence = "high" | "medium" | "low";

export interface SourceReference {
  document_name: string;
  page_number: number | null;
  // Aditivos desde ADR-0014: ausentes en mensajes anteriores a la Fase 9.
  document_title?: string | null;
  section?: string | null;
  page_end?: number | null;
}

export interface AnswerResponse {
  message_id: string;
  conversation_id: string;
  answer_text: string;
  // Nulos cuando la respuesta la resolvió una habilidad local (saludo, identidad,
  // guía): no es una afirmación sobre la normativa, así que no se evalúa contra
  // documentos ni lleva fuentes.
  is_grounded: boolean | null;
  confidence: VerificationConfidence | null;
  created_at: string;
  sources: SourceReference[];
}

export type MessageRole = "student" | "assistant";

export interface MessageDto {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
  is_grounded: boolean | null;
  confidence: VerificationConfidence | null;
  sources: SourceReference[];
}

export interface ConversationDto {
  id: string;
  created_at: string;
  messages: MessageDto[];
}

export type DocumentStatus = "pending" | "indexed" | "error";

export interface DocumentSummary {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  error_message: string | null;
}

export interface IngestResult {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  chunk_count: number;
  error_message: string | null;
}

export interface ApiErrorBody {
  detail: string;
}
