/**
 * HTTP client for the MazaoX API.
 *
 * - The access token lives in memory only (ADR-002); the refresh token is an httpOnly cookie the browser sends
 *   because every call uses `credentials: "include"`.
 * - The backend rotates and blacklists refresh tokens, so only ONE refresh may be in flight: every 401 waits for
 *   the same promise (also protects against React StrictMode running effects twice).
 * - Errors use the API envelope `{error: {code, message, details: [{field, message}]}}`.
 */
import type { Envelope, FieldError, User } from "./types";

export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8010/api/v1";
export const API_ORIGIN: string = new URL(API_URL, window.location.href).origin;

export class ApiError extends Error {
  status: number;
  code: string;
  details: FieldError[];
  constructor(status: number, code: string, message: string, details: FieldError[] = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
  /** First message per field, for showing next to form inputs. */
  get fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const d of this.details) if (d.field && !(d.field in out)) out[d.field] = d.message;
    return out;
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Something went wrong. Please try again.";
}

export interface Session {
  access: string;
  user: User;
}

let accessToken: string | null = null;
let refreshPromise: Promise<Session | null> | null = null;
type SessionListener = (user: User | null) => void;
const listeners = new Set<SessionListener>();

export function onSessionChange(listener: SessionListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
function emit(user: User | null) {
  listeners.forEach((l) => l(user));
}

export function setSession(session: Session | null) {
  accessToken = session?.access ?? null;
  emit(session?.user ?? null);
}
export function getAccessToken() {
  return accessToken;
}

async function parse(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function toError(res: Response, body: unknown): ApiError {
  const err = (body as { error?: { code?: string; message?: string; details?: FieldError[] } } | null)?.error;
  if (res.status === 429) {
    const wait = res.headers.get("Retry-After");
    return new ApiError(429, "RATE_LIMITED", wait ? `Too many requests. Please try again in ${wait} seconds.` : "Too many requests. Please wait a moment and try again.");
  }
  return new ApiError(res.status, err?.code ?? "ERROR", err?.message ?? "Something went wrong. Please try again.", err?.details ?? []);
}

/** Exchange the refresh cookie for a new access token. One call at a time, shared by all waiters. */
export function refreshSession(): Promise<Session | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_URL}/auth/refresh`, { method: "POST", credentials: "include" });
        if (!res.ok) {
          setSession(null);
          return null;
        }
        const body = (await parse(res)) as Envelope<Session>;
        setSession(body.data);
        return body.data;
      } catch {
        return null; // network trouble: keep whatever state we have
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  query?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  form?: FormData;
  auth?: boolean; // default true: send the bearer token when we have one
  idempotencyKey?: string;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]) {
  const url = new URL(`${API_URL}${path}`);
  if (query) for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  return url.toString();
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  if (opts.auth !== false && accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.idempotencyKey) headers["Idempotency-Key"] = opts.idempotencyKey;
  try {
    return await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? "GET",
      headers,
      credentials: "include",
      body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
      signal: opts.signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "NETWORK", "We can't reach the server. Check your connection and try again.");
  }
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<Envelope<T>> {
  let res = await send(path, opts);
  if (res.status === 401 && opts.auth !== false) {
    const session = await refreshSession(); // shared single flight
    if (session) res = await send(path, opts);
  }
  const body = await parse(res);
  if (!res.ok) throw toError(res, body);
  return (body ?? { data: null }) as Envelope<T>;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) => request<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown, extra: Partial<RequestOptions> = {}) => request<T>(path, { method: "POST", body, ...extra }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", form }),
};

/** Image URLs from the API are origin-relative (`/api/v1/media/...`): join with the API origin. */
export function mediaUrl(url: string): string {
  return url.startsWith("http") ? url : `${API_ORIGIN}${url}`;
}
