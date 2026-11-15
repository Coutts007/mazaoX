import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, onSessionChange, refreshSession, setSession, type Session } from "../api/client";
import type { Role, User } from "../api/types";

interface RegisterInput {
  full_name: string;
  email?: string;
  phone?: string;
  password: string;
  role: Exclude<Role, "admin">;
}

interface AuthState {
  user: User | null;
  /** false until the first attempt to restore the session (from the refresh cookie) has finished */
  ready: boolean;
  login: (identifier: string, password: string) => Promise<User>;
  register: (input: RegisterInput) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const off = onSessionChange(setUser);
    // Shared single-flight refresh: safe even when React StrictMode runs this effect twice.
    refreshSession().finally(() => setReady(true));
    return off;
  }, []);

  const login = useCallback(async (identifier: string, password: string) => {
    const res = await api.post<Session>("/auth/login", { identifier, password }, { auth: false });
    setSession(res.data);
    return res.data.user;
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    // The API creates the account and returns only the user; signing in is a separate, explicit step.
    await api.post<User>("/auth/register", input, { auth: false });
    const res = await api.post<Session>("/auth/login", { identifier: input.email || input.phone, password: input.password }, { auth: false });
    setSession(res.data);
    return res.data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* the local session ends either way */
    }
    setSession(null);
  }, []);

  const value = useMemo(() => ({ user, ready, login, register, logout }), [user, ready, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export function homeFor(role: Role): string {
  return role === "farmer" ? "/farm" : role === "admin" ? "/admin" : "/";
}
