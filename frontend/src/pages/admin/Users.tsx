import { useState } from "react";
import { api } from "../../api/client";
import type { AdminUser, Envelope } from "../../api/types";
import { Pager } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { TextField } from "../../components/Field";
import { useToast } from "../../components/Toasts";
import { shortDate } from "../../lib/format";
import { useAsync, useDebounced } from "../../lib/useAsync";
import { ReasonDialog, useUrlState } from "./shared";

const ROLES = [["", "All roles"], ["farmer", "Farmers"], ["buyer", "Buyers"], ["admin", "Admins"]];

export default function Users() {
  const url = useUrlState();
  const toast = useToast();
  const [q, setQ] = useState(url.get("q"));
  const dq = useDebounced(q, 300);
  const role = url.get("role");
  const active = url.get("active");
  const res = useAsync<Envelope<AdminUser[]>>((s) => api.get<AdminUser[]>("/admin/users", { q: dq, role, is_active: active, page: url.page, page_size: 15 }, s), [dq, role, active, url.page]);
  const [target, setTarget] = useState<AdminUser | null>(null);
  const users = res.data?.data ?? [];
  return (
    <div className="wrap page">
      <div className="page-head"><h1>Users</h1></div>
      <div className="wrap-row" style={{ marginBottom: 12 }}>
        <div className="grow"><TextField label="Search name, email or phone" value={q} onChange={(e) => { setQ(e.target.value); url.set({ q: e.target.value || null }); }} /></div>
        <div className="tabs" role="tablist" aria-label="Role">{ROLES.map(([v, l]) => <button key={v} role="tab" aria-selected={role === v} className={`chip ${role === v ? "on" : ""}`} onClick={() => url.set({ role: v || null })}>{l}</button>)}</div>
        <div className="tabs" role="tablist" aria-label="Status">{[["", "Any status"], ["true", "Active"], ["false", "Suspended"]].map(([v, l]) => <button key={v} role="tab" aria-selected={active === v} className={`chip ${active === v ? "on" : ""}`} onClick={() => url.set({ active: v || null })}>{l}</button>)}</div>
      </div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <Skeleton style={{ height: 240, borderRadius: 14 }} /> : users.length === 0 ? <EmptyState icon="👥" title="No users match">Try a different search or filter.</EmptyState> : (
        <div className="card table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Contact</th><th>Role</th><th>Joined</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>{users.map((u) => (
              <tr key={u.id}>
                <td><b>{u.full_name}</b></td><td>{u.email ?? u.phone}</td><td>{u.role}</td><td>{shortDate(u.date_joined)}</td>
                <td><span className={`badge ${u.is_active ? "b-ok" : "b-bad"}`}>{u.is_active ? "Active" : "Suspended"}</span></td>
                <td>{u.role !== "admin" && <button className="btn btn-ghost btn-sm" onClick={() => setTarget(u)}>{u.is_active ? "Suspend" : "Reinstate"}</button>}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
      <Pager pagination={res.data?.pagination} onPage={(n) => url.set({ page: n > 1 ? String(n) : null })} />
      {target && (
        <ReasonDialog
          title={target.is_active ? `Suspend ${target.full_name}?` : `Reinstate ${target.full_name}?`}
          confirmLabel={target.is_active ? "Suspend account" : "Reinstate account"} danger={target.is_active} required={target.is_active}
          intro={<p className="small muted">{target.is_active ? "They will be signed out and their listings are hidden from buyers. This is recorded in the audit log." : "They will be able to sign in again and their listings return."}</p>}
          onConfirm={async (reason) => { await api.patch(`/admin/users/${target.id}/status`, { is_active: !target.is_active, reason }); toast.success(target.is_active ? "Account suspended" : "Account reinstated"); res.reload(); }}
          onClose={() => setTarget(null)} />
      )}
    </div>
  );
}
