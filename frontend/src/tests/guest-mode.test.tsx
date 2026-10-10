import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/features/auth/auth-context";
import { LoginPage } from "@/features/auth/LoginPage";
import { AdminRoute, ProtectedRoute } from "@/features/auth/protected-route";
import { ChatHeader } from "@/features/chat/components/chat-header";
import { GuestNotice } from "@/features/chat/components/guest-notice";

const post = vi.fn();

vi.mock("@/shared/lib/api-client", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/shared/lib/api-client")>();
  return { ...original, apiClient: { ...original.apiClient, post: (...args: unknown[]) => post(...args) } };
});

const STORAGE_KEY = "asistente-rag.session";
const GUEST_RESPONSE = { user_id: "guest-1", email: null, role: "guest", session_token: "token-invitado" };

function renderApp(initialPath: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/sin-permiso" element={<p>Sin permiso</p>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/chat" element={<p>Chat</p>} />
              <Route element={<AdminRoute />}>
                <Route path="/admin" element={<p>Panel administrativo</p>} />
              </Route>
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  post.mockReset();
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("Modo invitado", () => {
  it("entra al chat sin correo ni contraseña desde el login", async () => {
    post.mockResolvedValue(GUEST_RESPONSE);
    const user = userEvent.setup();
    renderApp("/login");

    await user.click(screen.getByRole("button", { name: /continuar como invitado/i }));

    await waitFor(() => expect(screen.getByText("Chat")).toBeInTheDocument());
    expect(post).toHaveBeenCalledWith("/auth/guest");
  });

  it("guarda la sesión de invitado solo mientras dura la pestaña", async () => {
    post.mockResolvedValue(GUEST_RESPONSE);
    const user = userEvent.setup();
    renderApp("/login");

    await user.click(screen.getByRole("button", { name: /continuar como invitado/i }));

    await waitFor(() => expect(sessionStorage.getItem(STORAGE_KEY)).not.toBeNull());
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("explica el error si no se pudo abrir la sesión de invitado", async () => {
    post.mockRejectedValue(new Error("caída"));
    const user = userEvent.setup();
    renderApp("/login");

    await user.click(screen.getByRole("button", { name: /continuar como invitado/i }));

    expect(await screen.findByText(/no se pudo abrir la sesión de invitado/i)).toBeInTheDocument();
  });

  it("convive con el login institucional", () => {
    renderApp("/login");
    expect(screen.getByLabelText(/correo institucional/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /iniciar sesión/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continuar como invitado/i })).toBeInTheDocument();
  });

  it("nunca muestra el panel administrativo a un invitado", () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ userId: "guest-1", email: null, role: "guest", token: "token-invitado" }),
    );
    renderApp("/admin");
    expect(screen.getByText("Sin permiso")).toBeInTheDocument();
    expect(screen.queryByText("Panel administrativo")).not.toBeInTheDocument();
  });

  it("identifica la sesión con una insignia y un aviso discreto", () => {
    const { rerender } = render(<ChatHeader title={null} isOnline onOpenSidebar={() => {}} isGuest />);
    expect(screen.getByText("Invitado")).toBeInTheDocument();

    rerender(<ChatHeader title={null} isOnline onOpenSidebar={() => {}} />);
    expect(screen.queryByText("Invitado")).not.toBeInTheDocument();

    render(<GuestNotice />);
    expect(
      screen.getByText(/estás utilizando alexis como visitante\. algunas funciones están disponibles únicamente para usuarios institucionales/i),
    ).toBeInTheDocument();
  });
});
