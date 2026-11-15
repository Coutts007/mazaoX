import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, errorMessage } from "../api/client";
import type { DemandRequest, Envelope, Match } from "../api/types";
import { EmptyState, ErrorState, Skeleton } from "../components/Feedback";
import { SelectField, TextField } from "../components/Field";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toasts";
import { Pager } from "../components/Bits";
import { COUNTIES, UNITS } from "../lib/constants";
import { kes, qty, shortDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { ListingCard } from "../components/ListingCard";

const REASON: Record<string, string> = { name: "Same produce", unit: "Same unit", county: "Same county", within_target_price: "Within your price", enough_stock: "Enough stock" };

function NewRequest({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const tomorrow = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
  const [f, setF] = useState({ produce_name: "", quantity: "", quantity_unit: "kg", target_price_per_unit: "", county: "Nairobi", required_by: tomorrow });
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: string) => setF((x) => ({ ...x, [k]: v }));
  async function submit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!f.produce_name.trim()) local.produce_name = "What produce do you need?";
    if (!f.quantity || Number(f.quantity) <= 0) local.quantity = "Enter how much you need.";
    setErr(local);
    if (Object.keys(local).length) return;
    setBusy(true);
    try {
      await api.post("/demand-requests", { ...f, produce_name: f.produce_name.trim(), target_price_per_unit: f.target_price_per_unit || null });
      toast.success("Request posted. Farmers selling this produce were told.");
      onDone(); onClose();
    } catch (x) { setErr(x instanceof ApiError && x.details.length ? x.fieldErrors : { produce_name: errorMessage(x) }); }
    finally { setBusy(false); }
  }
  return (
    <Modal title="Post a request" onClose={onClose}>
      <form className="stack" onSubmit={submit} noValidate>
        <TextField label="Produce you need" value={f.produce_name} onChange={(e) => set("produce_name", e.target.value)} error={err.produce_name} placeholder="e.g. Potatoes" />
        <div className="wrap-row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}>
          <div className="grow"><TextField label="Quantity" inputMode="decimal" value={f.quantity} onChange={(e) => set("quantity", e.target.value.replace(/[^\d.]/g, ""))} error={err.quantity} /></div>
          <div style={{ width: 120 }}><SelectField label="Unit" value={f.quantity_unit} onChange={(e) => set("quantity_unit", e.target.value)} error={err.quantity_unit}>{UNITS.map((u) => <option key={u.value}>{u.value}</option>)}</SelectField></div>
        </div>
        <TextField label="Target price per unit (KES, optional)" inputMode="decimal" value={f.target_price_per_unit} onChange={(e) => set("target_price_per_unit", e.target.value.replace(/[^\d.]/g, ""))} error={err.target_price_per_unit} />
        <SelectField label="County" value={f.county} onChange={(e) => set("county", e.target.value)} error={err.county}>{COUNTIES.map((c) => <option key={c}>{c}</option>)}</SelectField>
        <TextField label="Needed by" type="date" value={f.required_by} onChange={(e) => set("required_by", e.target.value)} error={err.required_by} />
        <p className="muted small">Farmers see what you need but never your name or contact details. Nothing is ordered automatically.</p>
        <div className="modal-foot"><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>{busy ? "Posting…" : "Post request"}</button></div>
      </form>
    </Modal>
  );
}

function Matches({ request, onClose }: { request: DemandRequest; onClose: () => void }) {
  const res = useAsync((s) => api.get<Match[]>(`/demand-requests/${request.id}/matches`, undefined, s).then((r) => r.data), [request.id]);
  return (
    <Modal title={`Matches for ${request.produce_name}`} onClose={onClose}>
      {res.loading ? <Skeleton style={{ height: 120 }} /> : res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : !res.data?.length ? <EmptyState icon="🔎" title="No matching produce right now">We'll tell farmers about your request. Check back soon.</EmptyState> : (
        <div className="stack">
          <p className="muted small">These are suggestions only. Nothing is reserved or ordered until you place an order.</p>
          {res.data.map((m) => (
            <div key={m.listing.id} className="stack" style={{ gap: 6 }}>
              <ListingCard listing={m.listing} />
              <div className="wrap-row">{m.reasons.map((r) => <span key={r} className="badge b-ok">{REASON[r] ?? r}</span>)}<span className="muted small">{qty(m.available)} {m.listing.quantity_unit} available</span></div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

export default function Requests() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const res = useAsync<Envelope<DemandRequest[]>>((s) => api.get<DemandRequest[]>("/demand-requests", { page, page_size: 10 }, s), [page]);
  const [creating, setCreating] = useState(false);
  const [viewing, setViewing] = useState<DemandRequest | null>(null);
  const items = res.data?.data ?? [];
  async function close(r: DemandRequest) {
    try { await api.post(`/demand-requests/${r.id}/close`); toast.info("Request closed"); res.reload(); } catch (e) { toast.error(errorMessage(e)); }
  }
  return (
    <div className="wrap page">
      <div className="page-head"><div><h1>My requests</h1><p className="muted">Can't find it? Tell farmers what you need.</p></div><button className="btn btn-accent" onClick={() => setCreating(true)}>+ Post a request</button></div>
      <div className="stack">
        {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> :
          res.loading && !res.data ? <Skeleton style={{ height: 100, borderRadius: 14 }} /> :
          items.length === 0 ? <EmptyState icon="📣" title="No requests yet">Post what you need and farmers who grow it will be notified. <Link to="/browse">Or browse what's available now.</Link></EmptyState> :
          items.map((r) => (
            <div key={r.id} className="card card-pad stack">
              <div className="row"><b>{qty(r.quantity)} {r.quantity_unit} of {r.produce_name}</b><span className={`badge ${r.status === "open" ? "b-ok" : "b-off"}`}>{r.status}</span></div>
              <p className="muted small">{r.county} · Needed by {shortDate(r.required_by)}{r.target_price_per_unit ? ` · Target ${kes(r.target_price_per_unit)}/${r.quantity_unit}` : ""}</p>
              <div className="wrap-row"><button className="btn btn-ghost btn-sm" onClick={() => setViewing(r)}>See matches</button>{r.status === "open" && <button className="btn btn-text btn-sm" onClick={() => close(r)}>Close request</button>}</div>
            </div>
          ))}
      </div>
      <Pager pagination={res.data?.pagination} onPage={setPage} />
      {creating && <NewRequest onClose={() => setCreating(false)} onDone={res.reload} />}
      {viewing && <Matches request={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}
