import type { ApiErrorBody } from "@/shared/types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Las subidas de documentos pueden tardar; el resto no debería colgar nunca. */
const DEFAULT_TIMEOUT_MS = 30_000;
const UPLOAD_TIMEOUT_MS = 180_000;

export type ApiErrorKind = "network" | "timeout" | "session" | "forbidden" | "notFound" | "server";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public kind: ApiErrorKind = "server",
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** La sesión dejó de ser válida: hay que reautenticarse, no reintentar. */
  get isSessionExpired(): boolean {
    return this.kind === "session";
  }

  /** Reintentar tiene sentido: el problema es de transporte, no de la petición. */
  get isRetryable(): boolean {
    return this.kind === "network" || this.kind === "timeout" || this.status >= 500;
  }
}

/**
 * Mensajes en el idioma del usuario y orientados a la acción.
 *
 * Antes se mostraba el `detail` crudo del backend o "Error inesperado (HTTP 500)":
 * un código de estado no le dice a un estudiante qué hacer a continuación. Se
 * respeta el mensaje del servidor solo cuando está claramente redactado para una
 * persona (validaciones de formulario), que es el caso de 400 y 409.
 */
function humanMessage(status: number, serverDetail: string | null): string {
  if (status === 400 || status === 409 || status === 422) {
    return serverDetail ?? "Revisa los datos e inténtalo de nuevo.";
  }
  switch (status) {
    case 401:
      return "Tu sesión expiró. Vuelve a iniciar sesión para continuar.";
    case 403:
      return "No tienes permiso para realizar esta acción.";
    case 404:
      return "No encontramos lo que buscabas.";
    case 413:
      return "El archivo es demasiado grande. Intenta con uno más pequeño.";
    case 429:
      return "Demasiadas solicitudes seguidas. Espera un momento y vuelve a intentarlo.";
    default:
      return status >= 500
        ? "El servicio no está disponible en este momento. Inténtalo de nuevo en unos minutos."
        : (serverDetail ?? "No se pudo completar la acción.");
  }
}

function kindFor(status: number): ApiErrorKind {
  if (status === 401) return "session";
  if (status === 403) return "forbidden";
  if (status === 404) return "notFound";
  return "server";
}

/**
 * Se notifica a la aplicación cuando el servidor rechaza la sesión, para que el
 * cierre de sesión ocurra una sola vez y en un único lugar, en vez de que cada
 * pantalla tenga que comprobar el 401 por su cuenta.
 */
type SessionExpiredHandler = () => void;
let onSessionExpired: SessionExpiredHandler | null = null;

export function setSessionExpiredHandler(handler: SessionExpiredHandler | null): void {
  onSessionExpired = handler;
}

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE" | "PUT";
  body?: unknown;
  token?: string | null;
  isFormData?: boolean;
  timeoutMs?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    if (options.isFormData) {
      body = options.body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }
  }

  // Sin esto, con el backend caído la promesa nunca se resuelve y la interfaz
  // queda bloqueada de forma indefinida.
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(0, "La solicitud tardó demasiado. Revisa tu conexión.", "timeout");
    }
    throw new ApiError(0, "No hay conexión con el servidor. Revisa tu red.", "network");
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let serverDetail: string | null = null;
    try {
      const errorBody = (await response.json()) as ApiErrorBody;
      serverDetail = errorBody.detail ?? null;
    } catch {
      // el cuerpo de error no era JSON: se usa únicamente el mensaje por estado
    }

    if (response.status === 401) onSessionExpired?.();

    throw new ApiError(
      response.status,
      humanMessage(response.status, serverDetail),
      kindFor(response.status),
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const apiClient = {
  get: <T>(path: string, token?: string | null) => request<T>(path, { method: "GET", token }),
  post: <T>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: "POST", body, token }),
  postForm: <T>(path: string, formData: FormData, token?: string | null) =>
    request<T>(path, {
      method: "POST",
      body: formData,
      isFormData: true,
      token,
      timeoutMs: UPLOAD_TIMEOUT_MS,
    }),
  delete: <T>(path: string, token?: string | null) =>
    request<T>(path, { method: "DELETE", token }),
};
