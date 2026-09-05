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
}

export interface AnswerResponse {
  message_id: string;
  conversation_id: string;
  answer_text: string;
  is_grounded: boolean;
  confidence: VerificationConfidence;
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
