import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ToastProvider } from "../components/Toasts";
import Login from "./Login";
import Register from "./Register";

const user = { id: "u1", full_name: "Achieng Demo", email: "a@example.test", phone: null, role: "buyer", date_joined: "2026-01-01" };
const fetchMock = vi.fn();
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function mount(ui: React.ReactNode, path = "/login") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ToastProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<p>HOME PAGE</p>} />
            <Route path="/login" element={ui} />
            <Route path="/register" element={ui} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </MemoryRouter>,
  );
}

describe("auth pages", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    // session restore on load: no cookie
    fetchMock.mockImplementation(async (url: string) => (url.endsWith("/auth/refresh") ? json(401, { error: { code: "UNAUTHENTICATED", message: "x" } }) : json(404, {})));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("login validates locally before calling the API", async () => {
    mount(<Login />);
    await userEvent.click(await screen.findByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Enter your email or phone number.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith("/auth/login"))).toBe(false);
  });

  it("login shows the server's message for bad credentials and keeps the form", async () => {
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/login") ? json(401, { error: { code: "INVALID_CREDENTIALS", message: "Invalid credentials.", details: [] } }) : json(401, { error: { code: "U", message: "x" } }),
    );
    mount(<Login />);
    await userEvent.type(await screen.findByLabelText("Email or phone"), "a@example.test");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials.");
    expect(screen.getByLabelText("Email or phone")).toHaveValue("a@example.test");
  });

  it("login success leaves the page", async () => {
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/login") ? json(200, { data: { access: "tok", user } }) : json(401, { error: { code: "U", message: "x" } }),
    );
    mount(<Login />);
    await userEvent.type(await screen.findByLabelText("Email or phone"), "a@example.test");
    await userEvent.type(screen.getByLabelText("Password"), "Demo-Pass-12345");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("HOME PAGE")).toBeInTheDocument();
  });

  it("password can be shown and hidden", async () => {
    mount(<Login />);
    const pw = await screen.findByLabelText("Password");
    expect(pw).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(pw).toHaveAttribute("type", "text");
  });

  it("register maps server field errors next to the inputs", async () => {
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/register")
        ? json(400, { error: { code: "VALIDATION_ERROR", message: "bad", details: [{ field: "email", message: "This email is already registered." }] } })
        : json(401, { error: { code: "U", message: "x" } }),
    );
    mount(<Register />, "/register");
    await userEvent.type(await screen.findByLabelText("Full name"), "New Farmer");
    await userEvent.type(screen.getByLabelText("Email"), "taken@example.test");
    await userEvent.type(screen.getByLabelText("Password"), "Str0ng-Pass-123");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(screen.getByText("This email is already registered.")).toBeInTheDocument());
  });

  it("register requires an email or phone and a long enough password", async () => {
    mount(<Register />, "/register");
    await userEvent.type(await screen.findByLabelText("Full name"), "X Y");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Enter an email or a phone number.")).toBeInTheDocument();
    expect(screen.getByText("Use at least 8 characters.")).toBeInTheDocument();
  });
});
