import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { AdminSummary } from "../../api/types";
import { ErrorState, Skeleton } from "../../components/Feedback";
import { kes } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";

const n = (o: Record<string, number> | undefined, k: string) => o?.[k] ?? 0;

export default function Overview() {
  const res = useAsync((s) => api.get<AdminSummary>("/admin/reports/summary", undefined, s).then((r) => r.data), []);
  const d = res.data;
  return (
    <div className="wrap page">
      <div className="page-head"><h1>Platform overview</h1></div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : !d ? <Skeleton style={{ height: 220, borderRadius: 14 }} /> : (
        <>
          <div className="kpis">
            <Link className="kpi" to="/admin/users"><small>Users</small><b>{d.users.total}</b><small>{n(d.users.by_role, "farmer")} farmers · {n(d.users.by_role, "buyer")} buyers · {d.users.suspended} suspended</small></Link>
            <Link className="kpi" to="/admin/listings"><small>Listings</small><b>{d.listings.total}</b><small>{d.listings.active_visible} live · {d.listings.hidden_by_admin} hidden</small></Link>
            <Link className="kpi" to="/admin/orders"><small>Orders</small><b>{d.orders.total}</b><small>{n(d.orders.by_status, "paid")} paid · {n(d.orders.by_status, "pending_payment")} awaiting payment</small></Link>
            <div className="kpi"><small>Paid value (simulated)</small><b>{kes(d.orders.paid_value_ksh)}</b><small>Sandbox payments only</small></div>
            <Link className="kpi" to="/admin/issues?status=open"><small>Open issues</small><b>{n(d.issues.by_status, "open") + n(d.issues.by_status, "investigating")}</b><small>{d.issues.total} reported in total</small></Link>
            <Link className="kpi" to="/admin/reviews"><small>Reviews</small><b>{d.reviews.total}</b><small>{d.reviews.hidden} hidden</small></Link>
          </div>
          <div className="grid-2">
            <section className="card card-pad stack" aria-label="Deliveries and payments">
              <h3>Fulfilment</h3>
              <p className="small">Deliveries: {Object.entries(d.deliveries.by_status).map(([k, v]) => `${v} ${k}`).join(" · ") || "none yet"}</p>
              <p className="small">Payment attempts: {Object.entries(d.payments.by_status).map(([k, v]) => `${v} ${k}`).join(" · ") || "none yet"}</p>
              <p className="small">Demand requests: {Object.entries(d.demand_requests.by_status).map(([k, v]) => `${v} ${k}`).join(" · ") || "none yet"}</p>
            </section>
            <section className="card card-pad stack" aria-label="Quality">
              <h3>Quality inspections</h3>
              <p className="small">{d.inspections.total} recorded · {d.inspections.published} published to buyers</p>
              <p className="muted small">Only inspections recorded by an administrator are shown to buyers as independently inspected. Farmers' grades always stay labelled farmer-declared.</p>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
