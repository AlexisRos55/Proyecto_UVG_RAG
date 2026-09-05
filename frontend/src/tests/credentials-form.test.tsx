import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CredentialsForm } from "@/features/auth/components/credentials-form";

/**
 * Regression test for a real bug: none of the generated shadcn/ui components (Input,
 * Textarea, ...) use React.forwardRef, which only works with React 19's "ref as a prop"
 * model. On React 18 the ref from react-hook-form's register() was silently dropped, so
 * react-hook-form could never read the field's real value — every submit saw `undefined`
 * and Zod reported its default "Required" message even though the user had typed real
 * values (this project upgraded to React 19 to fix it, see chat history / commit).
 */
describe("CredentialsForm", () => {
  it("submits the actual typed email and password, not undefined", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(
      <CredentialsForm
        submitLabel="Iniciar sesión"
        pendingLabel="Ingresando..."
        isPending={false}
        onSubmit={handleSubmit}
      />,
    );

    await user.type(screen.getByLabelText(/correo institucional/i), "admin@uvg.edu.gt");
    // Exact match: a regex here also matches the password-visibility toggle button's
    // aria-label ("Mostrar contraseña"), which legitimately contains the same word.
    await user.type(screen.getByLabelText("Contraseña"), "admin123");
    await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    await waitFor(() => expect(handleSubmit).toHaveBeenCalledTimes(1));
    expect(handleSubmit).toHaveBeenCalledWith(
      { email: "admin@uvg.edu.gt", password: "admin123" },
      expect.anything(),
    );

    expect(screen.queryByText(/required/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/obligatorio/i)).not.toBeInTheDocument();
  });
});
