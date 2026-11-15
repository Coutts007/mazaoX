import { useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../../api/client";
import type { Envelope, Issue } from "../../api/types";
import { Pager } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { SelectField, TextAreaField } from "../../components/Field";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/Toasts";
import { dateTime, shortId } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";
import { STATUS_BADGE, useUrlState } from "./shared";

const STATUSES = ["open", "investigating", "resolved", "dismissed"];

export default function Issues() {
  const url = useUrlState();
  const toast = useToast();
  const status = url.get("status");
  const res = useAsync<Envelope<Issue[]>>((s) => api.get<Issue[]>("/admin/issues", { status, page: url.page, page_size: 10 }, s), [status, url.page]);
  const [target, setTarget] = useState<Issue | null>(null);
  const [next, setNext] = useState("investigating");
  const [resolution, setResolution] = useState("");
  const [err, setErr] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const items = res.data?.data ?? [];
  function open(i: Issue) { setTarget(i); setNext(i.status === "open" ? "investigating" : i.status); setResolution(i.resolution); setErr(undefined); }
  async function save() {
    if (!target) return;
    if ((next === "resolved" || next === "dismissed") && !resolution.trim()) { setErr("Add a note for the buyer explaining the outcome."); return; }
    setBusy(true);
    try { await api.patch(`/admin/issues/${target.id}`, { status: next, resolution: resolution.trim() }); toast.success("Issue updated"); setTarget(null); res.reload(); }
    catch (x) { setErr(errorMessage(x)); } finally { setBusy(false); }
  }
  return (
    <div className="wrap page">
      <div className="page-head"><h1>Reported issues</h1></div>
      <div className="tabs" role="tablist" aria-label="Issue status" style={{ marginBottom: 12 }}>{[["", "All"], ...STATUSES.map((s) => [s, s[0].toUpperCase() + s.slice(1)])].map(([v, l]) => <button key={v} role="tab" aria-selected={status === v} className={`chip ${status === v ? "on" : ""}`} onClick={() => url.set({ status: v || null })}>{l}</button>)}</div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <Skeleton style={{ height: 200, borderRadius: 14 }} /> : items.length === 0 ? <EmptyState icon="🛟" title="No issues here">Nothing to triage for this filter.</EmptyState> : (
        <div className="stack">{items.map((i) => (
          <div key={i.id} className="card card-pad stack" style={{ gap: 6 }}>
            <div className="row"><b>{i.category[0].toUpperCase() + i.category.slice(1)} · order <Link to={`/orders/${i.order_id}`}>#{shortId(i.order_id)}</Link></b><span className={`badge ${STATUS_BADGE[i.status]}`}>{i.status}</span></div>
            <p>{i.description}</p>
            {i.resolution && <p className="small"><b>Resolution:</b> {i.resolution}</p>}
            <div className="row"><span className="muted small">Reported {dateTime(i.created_at)}</span><button className="btn btn-ghost btn-sm" onClick={() => open(i)}>Update</button></div>
          </div>))}</div>
      )}
      <Pager pagination={res.data?.pagination} onPage={(n) => url.set({ page: n > 1 ? String(n) : null })} />
      {target && (
        <Modal title="Update issue" onClose={() => setTarget(null)} footer={<><button className="btn btn-ghost" onClick={() => setTarget(null)}>Cancel</button><button className="btn btn-primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save"}</button></>}>
          <div className="stack">
            <p className="small">{target.description}</p>
            <SelectField label="Status" value={next} onChange={(e) => setNext(e.target.value)}>{STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}</SelectField>
            <TextAreaField label="Note to the buyer" value={resolution} onChange={(e) => setResolution(e.target.value)} maxLength={2000} error={err} />
          </div>
        </Modal>
      )}
    </div>
  );
}
