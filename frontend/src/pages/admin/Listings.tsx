import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, errorMessage } from "../../api/client";
import type { Envelope, Inspection, Listing } from "../../api/types";
import { Pager } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { SelectField, TextAreaField, TextField } from "../../components/Field";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/Toasts";
import { kes, shortDate } from "../../lib/format";
import { useAsync, useDebounced } from "../../lib/useAsync";
import { ReasonDialog, useUrlState } from "./shared";

const RESULTS = [["passed", "Passed"], ["passed_with_notes", "Passed with notes"], ["failed", "Failed"]];
const today = () => new Date().toISOString().slice(0, 10);

function InspectionDialog({ listing, onClose }: { listing: Listing; onClose: () => void }) {
  const toast = useToast();
  const existing = useAsync((s) => api.get<Inspection[]>(`/listings/${listing.id}/inspections`, undefined, s).then((r) => r.data).catch(() => [] as Inspection[]), [listing.id]);
  const [f, setF] = useState({ inspected_on: today(), scope: "", result: "passed", assessed_grade: "", notes: "", is_published: true });
  const [correcting, setCorrecting] = useState<Inspection | null>(null);
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: string | boolean) => setF((x) => ({ ...x, [k]: v }));
  async function save() {
    const local: Record<string, string> = {};
    if (!f.scope.trim()) local.scope = "Say what was inspected (for example, the batch or lot).";
    setErr(local);
    if (Object.keys(local).length) return;
    setBusy(true);
    try {
      await api.post(`/listings/${listing.id}/inspections`, { ...f, scope: f.scope.trim() });
      toast.success(f.is_published ? "Inspection published to buyers" : "Inspection saved (not published)");
      setF({ ...f, scope: "", notes: "", assessed_grade: "" });
      existing.reload();
    } catch (x) { setErr(x instanceof ApiError && x.details.length ? x.fieldErrors : { scope: errorMessage(x) }); }
    finally { setBusy(false); }
  }
  return (
    <>
      <Modal title={`Quality inspection: ${listing.produce_name}`} onClose={onClose}>
        <div className="stack">
          <p className="small muted">Inspections are recorded by an administrator and shown to buyers as <b>independently inspected</b>, separately from the farmer's own declared grade ({listing.declared_grade || "none declared"}).</p>
          {(existing.data ?? []).map((i) => (
            <div key={i.id} className="alert alert-info"><div className="row"><b>{shortDate(i.inspected_on)} · {i.result.replace(/_/g, " ")}</b><button className="btn btn-text btn-sm" onClick={() => setCorrecting(i)}>Correct</button></div><p className="small">{i.scope}{i.assessed_grade ? ` · grade ${i.assessed_grade}` : ""}</p></div>
          ))}
          <h4>Record a new inspection</h4>
          <TextField label="Inspection date" type="date" value={f.inspected_on} max={today()} onChange={(e) => set("inspected_on", e.target.value)} error={err.inspected_on} />
          <TextField label="What was inspected" value={f.scope} onChange={(e) => set("scope", e.target.value)} error={err.scope} maxLength={255} />
          <SelectField label="Result" value={f.result} onChange={(e) => set("result", e.target.value)} error={err.result}>{RESULTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</SelectField>
          <TextField label="Assessed grade (optional)" value={f.assessed_grade} onChange={(e) => set("assessed_grade", e.target.value)} maxLength={80} />
          <TextAreaField label="Notes (optional)" value={f.notes} onChange={(e) => set("notes", e.target.value)} maxLength={1000} />
          <label className="check"><input type="checkbox" checked={f.is_published} onChange={(e) => set("is_published", e.target.checked)} /> Publish to buyers</label>
          <button className="btn btn-primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Record inspection"}</button>
        </div>
      </Modal>
      {correcting && (
        <ReasonDialog title="Correct inspection" label="Reason for the correction" required confirmLabel="Save correction"
          intro={<p className="small muted">The correction keeps the original details and is recorded in the audit log. Result is kept as “{correcting.result.replace(/_/g, " ")}”; use a new inspection for a different outcome.</p>}
          onConfirm={async (reason) => { await api.patch(`/inspections/${correcting.id}`, { inspected_on: correcting.inspected_on, scope: correcting.scope, result: correcting.result, assessed_grade: correcting.assessed_grade, notes: correcting.notes, is_published: true, reason }); toast.success("Inspection corrected"); existing.reload(); }}
          onClose={() => setCorrecting(null)} />
      )}
    </>
  );
}

export default function Listings() {
  const url = useUrlState();
  const toast = useToast();
  const [q, setQ] = useState(url.get("q"));
  const dq = useDebounced(q, 300);
  const hidden = url.get("hidden");
  const status = url.get("status");
  const res = useAsync<Envelope<Listing[]>>((s) => api.get<Listing[]>("/admin/listings", { q: dq, hidden, status, page: url.page, page_size: 12 }, s), [dq, hidden, status, url.page]);
  const [moderating, setModerating] = useState<Listing | null>(null);
  const [inspecting, setInspecting] = useState<Listing | null>(null);
  const items = res.data?.data ?? [];
  return (
    <div className="wrap page">
      <div className="page-head"><h1>Listing moderation</h1></div>
      <div className="wrap-row" style={{ marginBottom: 12 }}>
        <div className="grow"><TextField label="Search produce" value={q} onChange={(e) => { setQ(e.target.value); url.set({ q: e.target.value || null }); }} /></div>
        <div className="tabs" role="tablist" aria-label="Visibility">{[["", "All"], ["true", "Hidden by admin"], ["false", "Visible"]].map(([v, l]) => <button key={v} role="tab" aria-selected={hidden === v} className={`chip ${hidden === v ? "on" : ""}`} onClick={() => url.set({ hidden: v || null })}>{l}</button>)}</div>
        <div className="tabs" role="tablist" aria-label="Listing status">{[["", "Any"], ["active", "Live"], ["inactive", "Offline"]].map(([v, l]) => <button key={v} role="tab" aria-selected={status === v} className={`chip ${status === v ? "on" : ""}`} onClick={() => url.set({ status: v || null })}>{l}</button>)}</div>
      </div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <Skeleton style={{ height: 240, borderRadius: 14 }} /> : items.length === 0 ? <EmptyState icon="🧺" title="No listings match" /> : (
        <div className="stack">{items.map((l) => (
          <div key={l.id} className="card card-pad stack" style={{ gap: 6 }}>
            <div className="row"><b>{l.produce_name}</b><span className="wrap-row"><span className={`badge ${l.status === "active" ? "b-ok" : "b-off"}`}>{l.status === "active" ? "Live" : "Offline"}</span>{l.moderation_hidden && <span className="badge b-bad">Hidden by admin</span>}</span></div>
            <p className="small muted">{kes(l.price_per_unit)} / {l.quantity_unit} · {l.county} · {l.declared_grade ? `Farmer-declared: ${l.declared_grade}` : "No grade declared"}</p>
            {l.moderation_hidden && l.moderation_reason && <p className="small">Reason: {l.moderation_reason}</p>}
            <div className="wrap-row"><Link className="btn btn-text btn-sm" to={`/listings/${l.id}`}>View</Link><button className="btn btn-ghost btn-sm" onClick={() => setInspecting(l)}>Inspections</button><button className={`btn btn-sm ${l.moderation_hidden ? "btn-ghost" : "btn-danger"}`} onClick={() => setModerating(l)}>{l.moderation_hidden ? "Restore" : "Hide"}</button></div>
          </div>))}</div>
      )}
      <Pager pagination={res.data?.pagination} onPage={(n) => url.set({ page: n > 1 ? String(n) : null })} />
      {inspecting && <InspectionDialog listing={inspecting} onClose={() => setInspecting(null)} />}
      {moderating && (
        <ReasonDialog title={moderating.moderation_hidden ? "Restore listing?" : "Hide listing?"} confirmLabel={moderating.moderation_hidden ? "Restore listing" : "Hide listing"} danger={!moderating.moderation_hidden} required={!moderating.moderation_hidden}
          intro={<p className="small muted">{moderating.moderation_hidden ? "The listing becomes visible to buyers again." : "Buyers will no longer see this listing. The farmer is told it was hidden."}</p>}
          onConfirm={async (reason) => { await api.patch(`/admin/listings/${moderating.id}/moderation`, { hidden: !moderating.moderation_hidden, reason }); toast.success(moderating.moderation_hidden ? "Listing restored" : "Listing hidden"); res.reload(); }}
          onClose={() => setModerating(null)} />
      )}
    </div>
  );
}
