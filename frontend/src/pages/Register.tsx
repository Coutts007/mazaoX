import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, errorMessage } from "../api/client";
import { homeFor, useAuth } from "../auth/AuthContext";
import { PasswordField, TextField } from "../components/Field";
import { SITE_IMAGES } from "../config/images";
import { useBackground } from "../components/SiteImage";
import { useToast } from "../components/Toasts";

type Choice = "buyer" | "farmer";

export default function Register() {
  const bg = useBackground(SITE_IMAGES.authBackground);
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [params] = useSearchParams();
  const [role, setRole] = useState<Choice>(params.get("role") === "farmer" ? "farmer" : "buyer");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!fullName.trim()) local.full_name = "Enter your full name.";
    if (!email.trim() && !phone.trim()) local.email = "Enter an email or a phone number.";
    if (password.length < 8) local.password = "Use at least 8 characters.";
    setFields(local);
    setError(null);
    if (Object.keys(local).length) return;
    setBusy(true);
    try {
      const u = await register({ full_name: fullName.trim(), email: email.trim() || undefined, phone: phone.trim() || undefined, password, role });
      toast.success(role === "farmer" ? "Welcome to MazaoX! Let's set up your farm." : "Welcome to MazaoX! Find something fresh.");
      navigate(homeFor(u.role), { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.details.length) {
        const map = err.fieldErrors;
        if (!map.email && map.identifier) map.email = map.identifier;
        setFields(map);
        if (err.code !== "VALIDATION_ERROR") setError(err.message);
      } else setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-bg" style={bg}>
      <form className="glass stack" onSubmit={submit} noValidate>
        <div>
          <h1>Join MazaoX</h1>
          <p className="lead">Fresh produce, straight from Kenyan farms.</p>
        </div>
        <div className="seg" role="group" aria-label="I want to">
          <button type="button" aria-pressed={role === "buyer"} onClick={() => setRole("buyer")}>Buy produce</button>
          <button type="button" aria-pressed={role === "farmer"} onClick={() => setRole("farmer")}>Sell produce</button>
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <TextField label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} error={fields.full_name} autoComplete="name" />
        <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={fields.email} autoComplete="email" hint="Email or phone, you only need one." />
        <TextField label="Phone (optional)" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} error={fields.phone} autoComplete="tel" placeholder="07XX XXX XXX" />
        <PasswordField label="Password" value={password} onChange={(e) => setPassword(e.target.value)} error={fields.password} autoComplete="new-password" hint="At least 8 characters. Avoid common passwords." />
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? <span className="spinner" /> : null}{busy ? "Creating account…" : "Create account"}</button>
        <p style={{ textAlign: "center" }}>Already registered? <Link to="/login">Log in</Link></p>
      </form>
    </div>
  );
}
