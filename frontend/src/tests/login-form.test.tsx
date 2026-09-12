import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/features/auth/components/login-form";

function renderLoginForm(overrides: Partial<Parameters<typeof LoginForm>[0]> = {}) {
  const onSubmit = vi.fn();
  const onForgotPassword = vi.fn();
  render(
    <LoginForm
      isPending={false}
      onSubmit={onSubmit}
      onForgotPassword={onForgotPassword}
      {...overrides}
    />,
  );
  return { onSubmit, onForgotPassword };
}

describe("LoginForm", () => {
  it("envía el contrato que espera login(credentials), con rememberMe incluido", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderLoginForm();

    await user.type(screen.getByLabelText(/correo institucional/i), "admin@uvg.edu.gt");
    // Coincidencia exacta: un regex tambien casaria con el boton "Mostrar contraseña".
    await user.type(screen.getByLabelText("Contraseña"), "admin123");
    await user.click(screen.getByLabelText(/mantener sesión iniciada/i));
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith(
      { email: "admin@uvg.edu.gt", password: "admin123", rememberMe: true },
      expect.anything(),
    );
  });

  it("rechaza correos fuera del dominio institucional sin llamar al API", async () => {
    const user = userEvent.setup();
    const { onSubmit } = renderLoginForm();

    await user.type(screen.getByLabelText(/correo institucional/i), "alguien@gmail.com");
    await user.type(screen.getByLabelText("Contraseña"), "admin123");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/correo institucional/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("conecta el mensaje de error con su campo mediante aria-describedby", async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const email = screen.getByLabelText(/correo institucional/i);
    await user.type(email, "alguien@gmail.com");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    await waitFor(() => expect(email).toHaveAttribute("aria-invalid", "true"));
    const describedBy = email.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(document.getElementById(describedBy!)).toHaveTextContent(/@uvg\.edu\.gt/);
  });

  it("bloquea el botón y anuncia el progreso mientras se inicia sesión", () => {
    renderLoginForm({ isPending: true });

    const submit = screen.getByRole("button", { name: /iniciando sesión/i });
    expect(submit).toBeDisabled();
    expect(submit).toHaveAttribute("aria-busy", "true");
  });

  it("alterna la visibilidad de la contraseña", async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const password = screen.getByLabelText("Contraseña");
    expect(password).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    expect(password).toHaveAttribute("type", "text");

    await user.click(screen.getByRole("button", { name: "Ocultar contraseña" }));
    expect(password).toHaveAttribute("type", "password");
  });
});
