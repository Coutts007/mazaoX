import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { vi } from "vitest";
import type { Listing, User } from "../api/types";
import { AuthProvider } from "../auth/AuthContext";
import { CartProvider } from "../cart/CartContext";
import { ToastProvider } from "../components/Toasts";

export const buyer: User = { id: "buyer-1", full_name: "Achieng Demo", email: "a@example.test", phone: null, role: "buyer", date_joined: "2026-01-01T00:00:00Z" };

export function listing(over: Partial<Listing> = {}): Listing {
  return {
    id: "l1", farmer_id: "f1", category: { id: "c1", name: "Tomatoes", slug: "tomatoes" }, produce_name: "Roma Tomatoes", variety: "", description: "",
    declared_grade: "Farmer-declared Grade A", grade_source: "farmer_declared", grade_verified: false, images: [],
    availability: { available: "50.000", in_stock: true }, price_per_unit: "85.00", quantity_unit: "kg", county: "Meru", locality: "Imenti",
    harvest_date: null, status: "active", moderation_hidden: false, moderation_reason: "", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", ...over,
  };
}

export const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
export const ok = (data: unknown, extra: Record<string, unknown> = {}) => json(200, { data, ...extra });

type Handler = (url: URL, init: RequestInit) => Response | Promise<Response> | undefined;

/** Route-based fetch mock. The refresh call returns the buyer session by default. */
export function mockApi(handlers: Handler[], opts: { loggedIn?: boolean } = { loggedIn: true }) {
  const calls: { url: URL; init: RequestInit }[] = [];
  const fn = vi.fn(async (input: string, init: RequestInit = {}) => {
    const url = new URL(input);
    calls.push({ url, init });
    if (url.pathname.endsWith("/auth/refresh")) return opts.loggedIn ? ok({ access: "tok", user: buyer }) : json(401, { error: { code: "UNAUTHENTICATED", message: "x" } });
    for (const h of handlers) {
      const r = h(url, init);
      if (r) return r;
    }
    return json(404, { error: { code: "NOT_FOUND", message: "Not found." } });
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls, find: (path: string, method = "GET") => calls.filter((c) => c.url.pathname.endsWith(path) && (c.init.method ?? "GET") === method) };
}

function Where() {
  const l = useLocation();
  return <div data-testid="where">{l.pathname + l.search}</div>;
}

export function renderApp(ui: ReactNode, path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ToastProvider>
        <AuthProvider>
          <CartProvider>
            <Routes>
              <Route path="*" element={<>{ui}<Where /></>} />
            </Routes>
          </CartProvider>
        </AuthProvider>
      </ToastProvider>
    </MemoryRouter>,
  );
}
