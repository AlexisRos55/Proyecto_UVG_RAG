import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { apiClient } from "@/shared/lib/api-client";
import type { AuthResponse, UserRole } from "@/shared/types/api";

interface Session {
  userId: string;
  email: string;
  role: UserRole;
  token: string;
}

interface AuthContextValue {
  session: Session | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
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

function loadStoredSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadStoredSession);

  const persistSession = useCallback((next: Session | null) => {
    setSession(next);
    if (next) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await apiClient.post<AuthResponse>("/auth/login", { email, password });
      persistSession(sessionFromResponse(response));
    },
    [persistSession],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      const response = await apiClient.post<AuthResponse>("/auth/register", { email, password });
      persistSession(sessionFromResponse(response));
    },
    [persistSession],
  );

  const logout = useCallback(() => persistSession(null), [persistSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: session !== null,
      isAdmin: session?.role === "admin",
      login,
      register,
      logout,
    }),
    [session, login, register, logout],
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
