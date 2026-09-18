import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { apiClient, setSessionExpiredHandler } from "@/shared/lib/api-client";
import type { AuthResponse, UserRole } from "@/shared/types/api";

interface Session {
  userId: string;
  email: string;
  role: UserRole;
  token: string;
}

/**
 * Credenciales tal y como las emite el formulario de acceso. `rememberMe` es una
 * preferencia del cliente (dónde se guarda la sesión) y no viaja al API: el contrato de
 * `POST /auth/login` sólo declara `email` y `password`.
 */
export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

interface AuthContextValue {
  session: Session | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  /** Cierta cuando la sesión terminó por rechazo del servidor y no por decisión
   *  del usuario. Permite explicar por qué se pide iniciar sesión de nuevo. */
  sessionExpired: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const STORAGE_KEY = "asistente-rag.session";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function sessionFromResponse(response: AuthResponse): Session {
  return {
    userId: response.user_id,
    email: response.email,
    role: response.role,
    token: response.session_token,
  };
}

/**
 * "Mantener sesión iniciada" decide el almacén: `localStorage` sobrevive al cierre del
 * navegador, `sessionStorage` muere con la pestaña. Al leer se consultan ambos porque la
 * elección anterior del usuario no se conoce hasta encontrar la sesión.
 */
function storageFor(persistent: boolean): Storage {
  return persistent ? localStorage : sessionStorage;
}

function loadStoredSession(): Session | null {
  for (const storage of [localStorage, sessionStorage]) {
    try {
      const raw = storage.getItem(STORAGE_KEY);
      if (raw) {
        return JSON.parse(raw) as Session;
      }
    } catch {
      // almacenamiento no disponible (modo privado) o JSON corrupto: se ignora
    }
  }
  return null;
}

function clearStoredSession(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // almacenamiento no disponible: la sesión sólo vive en memoria
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadStoredSession);
  const [sessionExpired, setSessionExpired] = useState(false);

  const persistSession = useCallback((next: Session, persistent: boolean) => {
    setSession(next);
    setSessionExpired(false);
    clearStoredSession();
    try {
      storageFor(persistent).setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // almacenamiento no disponible: la sesión sólo vive en memoria
    }
  }, []);

  /**
   * Un único punto de salida ante un 401. Antes no existía: con el token vencido
   * las consultas fallaban en silencio y el chat mostraba la pantalla de
   * bienvenida como si el usuario acabara de llegar, aparentando pérdida de datos.
   *
   * La sesión vigente se consulta por referencia y no por dependencia del efecto,
   * para registrar el manejador una sola vez sin leer un valor obsoleto.
   */
  const sessionRef = useRef(session);
  sessionRef.current = session;

  useEffect(() => {
    setSessionExpiredHandler(() => {
      // Varias consultas pueden fallar a la vez: solo la primera cierra la sesión.
      if (sessionRef.current === null) return;
      sessionRef.current = null;
      clearStoredSession();
      setSession(null);
      setSessionExpired(true);
    });
    return () => setSessionExpiredHandler(null);
  }, []);

  const login = useCallback(
    async ({ email, password, rememberMe = false }: LoginCredentials) => {
      const response = await apiClient.post<AuthResponse>("/auth/login", { email, password });
      persistSession(sessionFromResponse(response), rememberMe);
    },
    [persistSession],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      const response = await apiClient.post<AuthResponse>("/auth/register", { email, password });
      persistSession(sessionFromResponse(response), true);
    },
    [persistSession],
  );

  const logout = useCallback(() => {
    setSession(null);
    setSessionExpired(false);
    clearStoredSession();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: session !== null,
      isAdmin: session?.role === "admin",
      sessionExpired,
      login,
      register,
      logout,
    }),
    [session, sessionExpired, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de un AuthProvider");
  }
  return context;
}
