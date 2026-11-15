import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError, errorMessage } from "../api/client";
import { homeFor, useAuth } from "../auth/AuthContext";
import { PasswordField, TextField } from "../components/Field";
import { SITE_IMAGES } from "../config/images";
import { useBackground } from "../components/SiteImage";
import { useToast } from "../components/Toasts";

export default function Login() {
  const bg = useBackground(SITE_IMAGES.authBackground);
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const from = (location.state as { from?: string } | null)?.from;
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});

  if (user) return <Navigate to={from ?? homeFor(user.role)} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!identifier.trim()) local.identifier = "Enter your email or phone number.";
    if (!password) local.password = "Enter your password.";
    setFields(local);
    setError(null);
    if (Object.keys(local).length) return;
    setBusy(true);
    try {
      const u = await login(identifier.trim(), password);
      toast.success(`Welcome back, ${u.full_name.split(" ")[0]}!`);
      navigate(from ?? homeFor(u.role), { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR") setFields(err.fieldErrors);
      else setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-bg" style={bg}>
      <form className="glass stack" onSubmit={submit} noValidate>
        <div>
          <h1>Welcome back</h1>
          <p className="lead">Log in to buy or sell fresh produce.</p>
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <TextField label="Email or phone" value={identifier} onChange={(e) => setIdentifier(e.target.value)} error={fields.identifier} autoComplete="username" autoFocus placeholder="you@example.com or 07…" />
        <PasswordField label="Password" value={password} onChange={(e) => setPassword(e.target.value)} error={fields.password} autoComplete="current-password" />
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? <span className="spinner" /> : null}{busy ? "Logging in…" : "Log in"}</button>
        <p style={{ textAlign: "center" }}>New to MazaoX? <Link to="/register">Create an account</Link></p>
      </form>
    </div>
  );
}
