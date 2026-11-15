import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, mediaUrl, refreshSession, setSession } from "./client";

const user = { id: "u1", full_name: "A B", email: "a@example.test", phone: null, role: "buyer" as const, date_joined: "2026-01-01" };

function json(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });
}

describe("api client", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    setSession(null);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shares ONE refresh call between concurrent 401s, then retries each request once", async () => {
    setSession({ access: "old", user });
    let refreshCalls = 0;
    fetchMock.mockImplementation(async (url: string, init: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls++;
        await new Promise((r) => setTimeout(r, 10));
        return json(200, { data: { access: "new", user } });
      }
      const auth = (init.headers as Record<string, string>).Authorization;
      return auth === "Bearer new" ? json(200, { data: { ok: url } }) : json(401, { error: { code: "UNAUTHENTICATED", message: "no" } });
    });
    const [a, b, c] = await Promise.all([api.get("/orders"), api.get("/notifications"), api.get("/profiles/me")]);
    expect(refreshCalls).toBe(1);
    expect([a.data, b.data, c.data]).toHaveLength(3);
  });

  it("returns null from refreshSession and clears the user when the cookie is invalid", async () => {
    fetchMock.mockResolvedValue(json(401, { error: { code: "UNAUTHENTICATED", message: "x" } }));
    const seen: unknown[] = [];
    const { onSessionChange } = await import("./client");
    const off = onSessionChange((u) => seen.push(u));
    expect(await refreshSession()).toBeNull();
    off();
    expect(seen).toEqual([null]);
  });

  it("gives up after a failed refresh and surfaces the 401", async () => {
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/refresh") ? json(401, { error: { code: "X", message: "x" } }) : json(401, { error: { code: "UNAUTHENTICATED", message: "Log in first." } }),
    );
    await expect(api.get("/orders")).rejects.toMatchObject({ status: 401, message: "Log in first." });
  });

  it("maps validation details to per-field messages", async () => {
    fetchMock.mockResolvedValue(
      json(400, { error: { code: "VALIDATION_ERROR", message: "bad", details: [{ field: "email", message: "Enter a valid email address." }, { field: "email", message: "second" }, { field: "password", message: "Too short." }] } }),
    );
    const err = await api.post("/auth/register", {}, { auth: false }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.fieldErrors).toEqual({ email: "Enter a valid email address.", password: "Too short." });
  });

  it("explains rate limiting and network failure in plain words", async () => {
    fetchMock.mockResolvedValueOnce(json(429, { detail: "throttled" }, { "Retry-After": "30" }));
    await expect(api.get("/listings")).rejects.toMatchObject({ code: "RATE_LIMITED", message: expect.stringContaining("30 seconds") });
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(api.get("/listings")).rejects.toMatchObject({ code: "NETWORK" });
  });

  it("sends credentials, the bearer token, the idempotency key and omits empty query values", async () => {
    setSession({ access: "tok", user });
    fetchMock.mockImplementation(async () => json(200, { data: [] }));
    await api.post("/orders", { a: 1 }, { idempotencyKey: "key-1" });
    await api.get("/listings", { q: "", county: "Kiambu", page: 2, min_price: undefined });
    const [, post] = fetchMock.mock.calls[0];
    expect(post.credentials).toBe("include");
    expect(post.headers).toMatchObject({ Authorization: "Bearer tok", "Idempotency-Key": "key-1", "Content-Type": "application/json" });
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/listings\?county=Kiambu&page=2$/);
  });

  it("joins origin-relative media URLs to the API origin, not the API prefix", () => {
    expect(mediaUrl("/api/v1/media/abc")).toBe("http://localhost:8010/api/v1/media/abc");
    expect(mediaUrl("https://cdn.example.test/x.jpg")).toBe("https://cdn.example.test/x.jpg");
  });
});
