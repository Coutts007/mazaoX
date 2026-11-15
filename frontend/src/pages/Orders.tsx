import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Envelope, Order } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Pager } from "../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../components/Feedback";
import { ORDER_STATUS_BADGE, ORDER_STATUS_LABEL } from "../lib/constants";
import { dateTime, kes, qty, shortId } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const TABS = [
  { value: "", label: "All" },
  { value: "pending_payment", label: "Awaiting payment" },
  { value: "paid", label: "Paid" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "expired", label: "Expired" },
];

export default function Orders() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const page = params.get("page") ?? "1";
  const farmer = user?.role === "farmer";
  const admin = user?.role === "admin";
  const res = useAsync<Envelope<Order[]>>((s) => api.get<Order[]>("/orders", { status, page, page_size: 10 }, s), [status, page]);
  const [, force] = useState(0);
  const set = (patch: Record<string, string | null>) => {
    const n = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) (v ? n.set(k, v) : n.delete(k));
    setParams(n, { replace: true });
    force((x) => x + 1);
  };
  const orders = res.data?.data ?? [];
  return (
    <div className="wrap page">
      <div className="page-head"><h1>{admin ? "All orders" : farmer ? "Incoming orders" : "My orders"}</h1>{!farmer && !admin && <Link className="btn btn-ghost btn-sm" to="/browse">Keep shopping</Link>}</div>
      <div className="tabs" role="tablist" aria-label="Order status">
        {TABS.map((t) => <button key={t.value} role="tab" aria-selected={status === t.value} className={`chip ${status === t.value ? "on" : ""}`} onClick={() => set({ status: t.value || null, page: null })}>{t.label}</button>)}
      </div>
      <div className="stack" style={{ marginTop: 12 }} aria-busy={res.loading}>
        {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> :
          res.loading && !res.data ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} style={{ height: 96, borderRadius: 14 }} />) :
          orders.length === 0 ? <EmptyState icon="🧾" title={status ? "No orders with this status" : "No orders yet"} action={farmer || admin ? undefined : { to: "/browse", label: "Find fresh produce" }}>{farmer ? "New orders from buyers will appear here." : "When you place an order it will show up here."}</EmptyState> :
          orders.map((o) => (
            <Link key={o.id} to={`/orders/${o.id}`} className="card card-pad card-hover order-row">
              <div className="row"><b>Order #{shortId(o.id)}</b><span className={`badge ${ORDER_STATUS_BADGE[o.status]}`}>{ORDER_STATUS_LABEL[o.status]}</span></div>
              <p className="muted small">{o.lines.map((l) => `${l.produce_name} ${qty(l.quantity)} ${l.quantity_unit}`).join(" · ")}</p>
              <div className="row"><span className="muted small">{dateTime(o.created_at)} · {o.delivery_method === "delivery" ? "Delivery" : "Collection"}</span><b className="price">{kes(o.total_amount)}</b></div>
            </Link>
          ))}
      </div>
      <Pager pagination={res.data?.pagination} onPage={(n) => set({ page: n > 1 ? String(n) : null })} />
    </div>
  );
}
