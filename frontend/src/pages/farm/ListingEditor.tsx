import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api, errorMessage, mediaUrl } from "../../api/client";
import type { Category, Listing, StockMovement, StockSummary, Envelope } from "../../api/types";
import { ErrorState, Skeleton } from "../../components/Feedback";
import { SelectField, TextAreaField, TextField } from "../../components/Field";
import { useToast } from "../../components/Toasts";
import { COUNTIES, UNITS } from "../../lib/constants";
import { dateTime, qty } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";

const MAX_BYTES = 5 * 1024 * 1024;
const MAX_PHOTOS = 8;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

/** Mirrors the server's rules so people get instant feedback; the server still validates everything. */
export function checkImage(file: File): string | null {
  if (!TYPES.includes(file.type)) return `${file.name}: use a JPEG, PNG or WebP photo.`;
  if (file.size > MAX_BYTES) return `${file.name}: photos must be 5 MB or smaller.`;
  return null;
}

function Photos({ listing, onChanged }: { listing: Listing; onChanged: () => void }) {
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  async function pick(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    const room = MAX_PHOTOS - listing.images.length;
    const errs: string[] = [];
    const good: File[] = [];
    for (const f of files) {
      const problem = checkImage(f);
      if (problem) errs.push(problem);
      else if (good.length >= room) errs.push(`${f.name}: you can add up to ${MAX_PHOTOS} photos.`);
      else good.push(f);
    }
    setBusy(true);
    for (const f of good) {
      const form = new FormData();
      form.append("image", f);
      try { await api.upload(`/listings/${listing.id}/media`, form); } catch (x) { errs.push(`${f.name}: ${errorMessage(x)}`); }
    }
    setBusy(false);
    setErrors(errs);
    if (good.length) { toast.success(`${good.length} photo${good.length > 1 ? "s" : ""} uploaded`); onChanged(); }
  }
  async function remove(id: string) {
    try { await api.del(`/listings/${listing.id}/media/${id}`); toast.info("Photo removed"); onChanged(); } catch (x) { toast.error(errorMessage(x)); }
  }
  return (
    <section className="card card-pad stack" aria-label="Photos">
      <div className="row"><h3>Photos</h3><span className="muted small">{listing.images.length}/{MAX_PHOTOS}</span></div>
      <div className="photo-grid">
        {listing.images.map((m) => (
          <div key={m.id} className="photo-item"><img src={mediaUrl(m.url)} alt="" /><button type="button" onClick={() => remove(m.id)} aria-label="Remove photo">✕</button></div>
        ))}
        {listing.images.length < MAX_PHOTOS && (
          <button type="button" className="photo-add" onClick={() => input.current?.click()} disabled={busy}>{busy ? <span className="spinner" /> : <><b>＋</b>Add photos</>}</button>
        )}
      </div>
      <input ref={input} type="file" accept={TYPES.join(",")} multiple hidden onChange={pick} aria-label="Choose photos" />
      <p className="muted small">JPEG, PNG or WebP, up to 5 MB each. Location data is stripped from photos automatically.</p>
      {errors.map((e) => <div key={e} className="alert alert-error" role="alert">{e}</div>)}
    </section>
  );
}

function Stock({ listing }: { listing: Listing }) {
  const toast = useToast();
  const summary = useAsync((s) => api.get<StockSummary>(`/inventory/listings/${listing.id}`, undefined, s).then((r) => r.data), [listing.id]);
  const moves = useAsync<Envelope<StockMovement[]>>((s) => api.get<StockMovement[]>(`/inventory/listings/${listing.id}/movements`, { page_size: 8 }, s), [listing.id]);
  const [type, setType] = useState("addition");
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!quantity || Number(quantity) === 0 || Number.isNaN(Number(quantity))) local.quantity = "Enter a quantity.";
    if (type !== "addition" && !reason.trim()) local.reason = "A reason is required for this change.";
    setErr(local);
    if (Object.keys(local).length) return;
    setBusy(true);
    try {
      await api.post(`/inventory/listings/${listing.id}/adjustments`, { movement_type: type, quantity, reason: reason.trim() });
      toast.success("Stock updated");
      setQuantity(""); setReason("");
      summary.reload(); moves.reload();
    } catch (x) { setErr(x instanceof ApiError && x.details.length ? x.fieldErrors : { quantity: errorMessage(x) }); }
    finally { setBusy(false); }
  }
  const s = summary.data;
  return (
    <section className="card card-pad stack" aria-label="Stock">
      <h3>Stock</h3>
      {summary.error ? <ErrorState message={summary.error} onRetry={summary.reload} /> : !s ? <Skeleton style={{ height: 60 }} /> : (
        <div className="kpis" style={{ marginBottom: 0 }}>
          <div className="kpi"><small>On hand</small><b>{qty(s.on_hand)}</b></div>
          <div className="kpi"><small>Held for open orders</small><b>{qty(s.reserved)}</b></div>
          <div className="kpi"><small>Available to buyers</small><b>{qty(s.available)}</b></div>
        </div>
      )}
      <form className="stack" onSubmit={submit} noValidate>
        <SelectField label="What happened?" value={type} onChange={(e) => setType(e.target.value)} error={err.movement_type}>
          <option value="addition">I harvested / added stock</option>
          <option value="spoilage">Some spoiled or was lost</option>
          <option value="correction">Correct the count (use − to reduce)</option>
        </SelectField>
        <TextField label={`Quantity (${listing.quantity_unit})`} inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value.replace(/[^\d.-]/g, ""))} error={err.quantity} />
        <TextField label={type === "addition" ? "Note (optional)" : "Reason"} value={reason} onChange={(e) => setReason(e.target.value)} error={err.reason} maxLength={255} />
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Update stock"}</button>
      </form>
      {(moves.data?.data ?? []).length > 0 && (
        <div className="table-wrap"><table><thead><tr><th>When</th><th>Change</th><th>Balance</th><th>Why</th></tr></thead><tbody>
          {moves.data!.data.map((m) => <tr key={m.id}><td>{dateTime(m.created_at)}</td><td className={Number(m.quantity_delta) < 0 ? "warn" : ""}>{Number(m.quantity_delta) > 0 ? "+" : ""}{qty(m.quantity_delta)}</td><td>{qty(m.resulting_on_hand)}</td><td>{m.reason || m.movement_type}</td></tr>)}
        </tbody></table></div>
      )}
    </section>
  );
}

interface FormState {
  category_id: string; produce_name: string; variety: string; description: string; declared_grade: string;
  price_per_unit: string; quantity_unit: string; county: string; locality: string; harvest_date: string;
}
const blank: FormState = { category_id: "", produce_name: "", variety: "", description: "", declared_grade: "", price_per_unit: "", quantity_unit: "kg", county: "", locality: "", harvest_date: "" };

export default function ListingEditor() {
  const { id } = useParams();
  const editing = !!id;
  const navigate = useNavigate();
  const toast = useToast();
  const categories = useAsync((s) => api.get<Category[]>("/categories", undefined, s).then((r) => r.data), []);
  const existing = useAsync((s) => (id ? api.get<Listing>(`/listings/${id}`, undefined, s).then((r) => r.data) : Promise.resolve(null)), [id]);
  const [f, setF] = useState<FormState>(blank);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const l = existing.data;
  if (l && loadedFor !== l.id) {
    setLoadedFor(l.id);
    setF({ category_id: l.category.id, produce_name: l.produce_name, variety: l.variety, description: l.description, declared_grade: l.declared_grade, price_per_unit: l.price_per_unit, quantity_unit: l.quantity_unit, county: l.county, locality: l.locality, harvest_date: l.harvest_date ?? "" });
  }
  const set = (k: keyof FormState, v: string) => setF((x) => ({ ...x, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!f.category_id) local.category_id = "Choose a category.";
    if (!f.produce_name.trim()) local.produce_name = "What are you selling?";
    if (!f.price_per_unit || Number(f.price_per_unit) <= 0) local.price_per_unit = "Enter a price greater than zero.";
    if (!f.county) local.county = "Choose your county.";
    setErr(local);
    if (Object.keys(local).length) return;
    const body: Record<string, unknown> = { ...f, produce_name: f.produce_name.trim(), harvest_date: f.harvest_date || null };
    setBusy(true);
    try {
      if (editing) {
        await api.patch(`/listings/${id}`, body);
        toast.success("Listing saved");
        existing.reload();
      } else {
        const res = await api.post<Listing>("/listings", body);
        toast.success("Listing created. Now add photos and your stock.");
        navigate(`/farm/listings/${res.data.id}`, { replace: true });
      }
    } catch (x) { setErr(x instanceof ApiError && x.details.length ? x.fieldErrors : { produce_name: errorMessage(x) }); }
    finally { setBusy(false); }
  }
  async function toggle() {
    if (!l) return;
    try { await api.post(`/listings/${l.id}/${l.status === "active" ? "deactivate" : "activate"}`); toast.success(l.status === "active" ? "Listing taken offline" : "Listing is live"); existing.reload(); } catch (x) { toast.error(errorMessage(x)); }
  }

  if (editing && existing.loading && !l) return <div className="wrap page"><Skeleton style={{ height: 300, borderRadius: 14 }} /></div>;
  if (editing && existing.error) return <div className="wrap"><ErrorState message={existing.error} onRetry={existing.reload} /></div>;

  return (
    <div className="wrap page">
      <nav className="crumbs"><Link to="/farm/listings">My listings</Link> › <span>{editing ? l?.produce_name : "New listing"}</span></nav>
      <div className="page-head">
        <h1>{editing ? "Edit listing" : "New listing"}</h1>
        {l && <div className="wrap-row"><span className={`badge ${l.moderation_hidden ? "b-bad" : l.status === "active" ? "b-ok" : "b-off"}`}>{l.moderation_hidden ? "Hidden by admin" : l.status === "active" ? "Live" : "Not listed"}</span><button className="btn btn-ghost btn-sm" onClick={toggle}>{l.status === "active" ? "Take offline" : "Put live"}</button><Link className="btn btn-text btn-sm" to={`/listings/${l.id}`}>View as buyer</Link></div>}
      </div>
      {l?.moderation_hidden && <div className="alert alert-error" role="alert" style={{ marginBottom: 12 }}>An administrator hid this listing{l.moderation_reason ? `: ${l.moderation_reason}` : "."}</div>}
      <div className="editor">
        <form className="card card-pad stack" onSubmit={submit} noValidate>
          <SelectField label="Category" value={f.category_id} onChange={(e) => set("category_id", e.target.value)} error={err.category_id}><option value="">Select…</option>{categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</SelectField>
          <TextField label="Produce name" value={f.produce_name} onChange={(e) => set("produce_name", e.target.value)} error={err.produce_name} maxLength={120} placeholder="e.g. Roma tomatoes" />
          <TextField label="Variety (optional)" value={f.variety} onChange={(e) => set("variety", e.target.value)} error={err.variety} maxLength={120} />
          <TextAreaField label="Description (optional)" value={f.description} onChange={(e) => set("description", e.target.value)} error={err.description} maxLength={2000} />
          <TextField label="Your quality grade (optional)" value={f.declared_grade} onChange={(e) => set("declared_grade", e.target.value)} error={err.declared_grade} maxLength={80} hint="Buyers will see this labelled as farmer-declared, not independently verified." />
          <div className="wrap-row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}>
            <div className="grow"><TextField label="Price per unit (KES)" inputMode="decimal" value={f.price_per_unit} onChange={(e) => set("price_per_unit", e.target.value.replace(/[^\d.]/g, ""))} error={err.price_per_unit} /></div>
            <div style={{ width: 130 }}><SelectField label="Sold by" value={f.quantity_unit} onChange={(e) => set("quantity_unit", e.target.value)} error={err.quantity_unit}>{UNITS.map((u) => <option key={u.value}>{u.value}</option>)}</SelectField></div>
          </div>
          <SelectField label="County" value={f.county} onChange={(e) => set("county", e.target.value)} error={err.county}><option value="">Select…</option>{COUNTIES.map((c) => <option key={c}>{c}</option>)}</SelectField>
          <TextField label="Area / locality (optional)" value={f.locality} onChange={(e) => set("locality", e.target.value)} error={err.locality} maxLength={100} />
          <TextField label="Harvest date (optional)" type="date" value={f.harvest_date} onChange={(e) => set("harvest_date", e.target.value)} error={err.harvest_date} />
          <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Create listing"}</button>
        </form>
        <div className="stack">
          {l ? (<><Photos listing={l} onChanged={existing.reload} /><Stock listing={l} /></>) : (
            <div className="card card-pad stack"><h3>What happens next</h3><p className="muted">After you create the listing you can add photos and set how much stock you have. Buyers can't order until there is stock.</p></div>
          )}
        </div>
      </div>
    </div>
  );
}
