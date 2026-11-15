import { api } from "../../api/client";
import type { AuditLog, Envelope } from "../../api/types";
import { Pager } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { SelectField } from "../../components/Field";
import { dateTime, shortId } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";
import { useUrlState } from "./shared";

const ACTIONS = ["user.suspended", "user.reinstated", "listing.hidden", "listing.restored", "review.hidden", "review.restored", "issue.updated", "inspection.created", "inspection.corrected"];

export default function Audit() {
  const url = useUrlState();
  const action = url.get("action");
  const targetType = url.get("target_type");
  const res = useAsync<Envelope<AuditLog[]>>((s) => api.get<AuditLog[]>("/admin/audit-logs", { action, target_type: targetType, page: url.page, page_size: 20 }, s), [action, targetType, url.page]);
  const logs = res.data?.data ?? [];
  return (
    <div className="wrap page">
      <div className="page-head"><h1>Audit log</h1></div>
      <p className="muted small" style={{ marginBottom: 12 }}>A read-only record of sensitive actions: who did what, to what, and when.</p>
      <div className="wrap-row" style={{ marginBottom: 12 }}>
        <div style={{ minWidth: 220 }}><SelectField label="Action" value={action} onChange={(e) => url.set({ action: e.target.value || null })}><option value="">All actions</option>{ACTIONS.map((a) => <option key={a}>{a}</option>)}</SelectField></div>
        <div className="tabs" role="tablist" aria-label="Target type">{["", "user", "listing", "review", "issue", "inspection"].map((v) => <button key={v} role="tab" aria-selected={targetType === v} className={`chip ${targetType === v ? "on" : ""}`} onClick={() => url.set({ target_type: v || null })}>{v || "All"}</button>)}</div>
      </div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <Skeleton style={{ height: 240, borderRadius: 14 }} /> : logs.length === 0 ? <EmptyState icon="📜" title="No entries match" /> : (
        <div className="card table-wrap">
          <table>
            <thead><tr><th>When</th><th>Action</th><th>Target</th><th>Actor</th><th>Detail</th></tr></thead>
            <tbody>{logs.map((l) => (
              <tr key={l.id}><td className="small">{dateTime(l.created_at)}</td><td><b>{l.action}</b></td><td className="small">{l.target_type} <span className="mono">{shortId(l.target_id)}</span></td><td className="small mono">{l.actor_id ? shortId(l.actor_id) : "system"}</td><td className="small">{Object.entries(l.detail ?? {}).map(([k, v]) => `${k}: ${String(v)}`).join(" · ")}</td></tr>))}</tbody>
          </table>
        </div>
      )}
      <Pager pagination={res.data?.pagination} onPage={(n) => url.set({ page: n > 1 ? String(n) : null })} />
    </div>
  );
}
