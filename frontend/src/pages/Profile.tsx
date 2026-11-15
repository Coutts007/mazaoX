import { useEffect, useState, type FormEvent } from "react";
import { ApiError, api, errorMessage } from "../api/client";
import type { Profile as P } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorState, Skeleton } from "../components/Feedback";
import { SelectField, TextAreaField, TextField } from "../components/Field";
import { useToast } from "../components/Toasts";
import { COUNTIES } from "../lib/constants";
import { shortDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function Profile() {
  const { user } = useAuth();
  const toast = useToast();
  const res = useAsync((s) => api.get<P>("/profiles/me", undefined, s).then((r) => r.data), []);
  const [f, setF] = useState({ county: "", locality: "", farm_name: "", bio: "" });
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (res.data) setF({ county: res.data.county, locality: res.data.locality, farm_name: res.data.farm_name, bio: res.data.bio }); }, [res.data]);
  const set = (k: string, v: string) => setF((x) => ({ ...x, [k]: v }));
  if (!user) return null;
  if (res.error) return <div className="wrap"><ErrorState message={res.error} onRetry={res.reload} /></div>;

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setErr({});
    try {
      const body: Record<string, string> = { county: f.county, locality: f.locality, bio: f.bio };
      if (user!.role === "farmer") body.farm_name = f.farm_name;
      await api.patch("/profiles/me", body);
      toast.success("Profile saved");
      res.reload();
    } catch (x) { if (x instanceof ApiError && x.details.length) setErr(x.fieldErrors); else toast.error(errorMessage(x)); }
    finally { setBusy(false); }
  }

  return (
    <div className="wrap page" style={{ maxWidth: 720 }}>
      <div className="page-head"><h1>My profile</h1></div>
      <div className="card card-pad stack" style={{ marginBottom: 16 }}>
        <div className="row"><b>{user.full_name}</b><span className="badge b-ok">{user.role}</span></div>
        <p className="muted small">{user.email ?? user.phone} · Member since {shortDate(user.date_joined)}</p>
      </div>
      {res.loading && !res.data ? <Skeleton style={{ height: 260, borderRadius: 14 }} /> : (
        <form className="card card-pad stack" onSubmit={save}>
          {user.role === "farmer" && <TextField label="Farm name" value={f.farm_name} onChange={(e) => set("farm_name", e.target.value)} error={err.farm_name} maxLength={120} hint="Shown to buyers on your listings." />}
          <SelectField label="County" value={f.county} onChange={(e) => set("county", e.target.value)} error={err.county}><option value="">Select a county</option>{COUNTIES.map((c) => <option key={c}>{c}</option>)}</SelectField>
          <TextField label="Area / locality" value={f.locality} onChange={(e) => set("locality", e.target.value)} error={err.locality} maxLength={100} />
          <TextAreaField label={user.role === "farmer" ? "About your farm" : "About you"} value={f.bio} onChange={(e) => set("bio", e.target.value)} error={err.bio} maxLength={500} hint={user.role === "farmer" ? "Buyers see this on your public farm page." : undefined} />
          <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
        </form>
      )}
    </div>
  );
}
