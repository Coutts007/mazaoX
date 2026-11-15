import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Envelope, Notification } from "../api/types";
import { Pager } from "../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../components/Feedback";
import { useToast } from "../components/Toasts";
import { timeAgo } from "../lib/format";
import { useAsync } from "../lib/useAsync";


export default function Notifications() {
  const [params, setParams] = useSearchParams();
  const page = params.get("page") ?? "1";
  const unreadOnly = params.get("unread") === "1";
  const res = useAsync<Envelope<Notification[]>>((s) => api.get<Notification[]>("/notifications", { page, page_size: 15, unread: unreadOnly ? "true" : undefined }, s), [page, unreadOnly]);
  const navigate = useNavigate();
  const toast = useToast();
  const items = res.data?.data ?? [];
  const unread = res.data?.unread_count ?? 0;

  async function open(n: Notification) {
    if (!n.is_read) {
      try { await api.post(`/notifications/${n.id}/read`); window.dispatchEvent(new Event("mazaox:notifications-changed")); } catch { /* opening still works */ }
    }
    if (n.order_id) navigate(`/orders/${n.order_id}`);
    else res.reload();
  }
  async function markAll() {
    const unreadItems = items.filter((n) => !n.is_read);
    await Promise.allSettled(unreadItems.map((n) => api.post(`/notifications/${n.id}/read`)));
    window.dispatchEvent(new Event("mazaox:notifications-changed"));
    toast.success("Marked as read");
    res.reload();
  }

  return (
    <div className="wrap page">
      <div className="page-head">
        <div><h1>Notifications</h1><p className="muted">{unread ? `${unread} unread` : "You're all caught up"}</p></div>
        <div className="wrap-row">
          <button className={`chip ${unreadOnly ? "on" : ""}`} aria-pressed={unreadOnly} onClick={() => { const n = new URLSearchParams(); if (!unreadOnly) n.set("unread", "1"); setParams(n, { replace: true }); }}>Unread only</button>
          {items.some((n) => !n.is_read) && <button className="btn btn-ghost btn-sm" onClick={markAll}>Mark page as read</button>}
        </div>
      </div>
      <div className="stack">
        {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> :
          res.loading && !res.data ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} style={{ height: 70, borderRadius: 14 }} />) :
          items.length === 0 ? <EmptyState icon="🔔" title={unreadOnly ? "Nothing unread" : "No notifications yet"}>Order and payment updates will show up here.</EmptyState> :
          items.map((n) => (
            <button key={n.id} className={`card card-pad card-hover notif ${n.is_read ? "" : "unread"}`} onClick={() => open(n)}>
              <span className="notif-dot" aria-hidden="true" />
              <span className="grow"><b>{n.title}</b><span className="muted small" style={{ display: "block" }}>{n.message}</span></span>
              <span className="muted small">{timeAgo(n.created_at)}</span>
              {!n.is_read && <span className="unread-dot" aria-label="Unread" />}
            </button>
          ))}
      </div>
      <Pager pagination={res.data?.pagination} onPage={(n) => { const q = new URLSearchParams(params); n > 1 ? q.set("page", String(n)) : q.delete("page"); setParams(q, { replace: true }); }} />
    </div>
  );
}
