import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { Envelope, Listing, Order, Review } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { ErrorState, Skeleton } from "../../components/Feedback";
import { ORDER_STATUS_BADGE, ORDER_STATUS_LABEL } from "../../lib/constants";
import { kes, qty, shortId, timeAgo } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";

const LOW = 20;

export default function FarmDashboard() {
  const { user } = useAuth();
  const listings = useAsync((s) => api.get<Listing[]>("/listings", { mine: "true", page_size: 50 }, s), []);
  const orders = useAsync((s) => api.get<Order[]>("/orders", { page_size: 50 }, s), []);
  const reviews = useAsync<Envelope<Review[]>>((s) => api.get<Review[]>(`/farmers/${user!.id}/reviews`, { page_size: 1 }, s), [user?.id]);

  const my = listings.data?.data ?? [];
  const ord = orders.data?.data ?? [];
  const summary = (reviews.data as unknown as { summary?: { average_rating: number | null; review_count: number } } | null)?.summary;
  const weekAgo = Date.now() - 7 * 864e5;
  const sales = ord.filter((o) => (o.status === "paid" || o.status === "completed") && new Date(o.created_at).getTime() >= weekAgo).reduce((n, o) => n + Number(o.total_amount), 0);
  const toPrepare = ord.filter((o) => o.status === "paid").length;
  const waiting = ord.filter((o) => o.status === "pending_payment").length;
  const active = my.filter((l) => l.status === "active" && !l.moderation_hidden);
  const low = my.filter((l) => l.status === "active" && l.availability && Number(l.availability.available) <= LOW);
  const hidden = my.filter((l) => l.moderation_hidden);
  const loading = listings.loading || orders.loading;

  return (
    <div className="wrap page">
      <div className="page-head">
        <div><h1>Karibu, {user?.full_name.split(" ")[0]}</h1><p className="muted">Here is how your farm is doing.</p></div>
        <Link className="btn btn-primary" to="/farm/listings/new">+ New listing</Link>
      </div>
      {(listings.error || orders.error) && <ErrorState message={listings.error ?? orders.error ?? ""} onRetry={() => { listings.reload(); orders.reload(); }} />}
      {hidden.length > 0 && <div className="alert alert-error" role="alert" style={{ marginBottom: 12 }}>{hidden.length} of your listings {hidden.length === 1 ? "was" : "were"} hidden by an administrator. Open {hidden.length === 1 ? "it" : "them"} to see the reason.</div>}

      <div className="kpis">
        <div className="kpi"><small>Paid sales, last 7 days</small><b>{loading ? "…" : kes(sales)}</b><span className="muted small">From your latest {Math.min(ord.length, 50)} orders</span></div>
        <Link to="/farm/orders?status=paid" className="kpi"><small>Orders to prepare</small><b>{loading ? "…" : toPrepare}</b><span className="muted small">{waiting} awaiting payment</span></Link>
        <Link to="/farm/listings" className="kpi"><small>Active listings</small><b>{loading ? "…" : active.length}</b><span className={low.length ? "warn small" : "muted small"}>{low.length ? `${low.length} low on stock` : "Stock looks fine"}</span></Link>
        <Link to="/farm/reviews" className="kpi"><small>Rating</small><b>{summary?.average_rating ? `${summary.average_rating} ★` : "–"}</b><span className="muted small">{summary?.review_count ?? 0} review{summary?.review_count === 1 ? "" : "s"}</span></Link>
      </div>

      <div className="two-col">
        <section className="card card-pad stack" aria-label="Recent orders">
          <div className="row"><h3>Recent orders</h3><Link to="/farm/orders">All orders →</Link></div>
          {loading ? <Skeleton style={{ height: 120 }} /> : ord.length === 0 ? <p className="muted">No orders yet. Once buyers order, they show up here.</p> : (
            <div className="table-wrap"><table>
              <thead><tr><th>Order</th><th>Items</th><th>Total</th><th>Status</th></tr></thead>
              <tbody>{ord.slice(0, 6).map((o) => (
                <tr key={o.id}><td><Link to={`/orders/${o.id}`}>#{shortId(o.id)}</Link><div className="muted small">{timeAgo(o.created_at)}</div></td><td>{o.lines.map((l) => `${l.produce_name} ${qty(l.quantity)} ${l.quantity_unit}`).join(", ")}</td><td>{kes(o.total_amount)}</td><td><span className={`badge ${ORDER_STATUS_BADGE[o.status]}`}>{ORDER_STATUS_LABEL[o.status]}</span></td></tr>
              ))}</tbody>
            </table></div>
          )}
        </section>
        <section className="card card-pad stack" aria-label="Stock alerts">
          <h3>Needs attention</h3>
          {low.length === 0 && my.length > 0 && <p className="muted">All your listings have healthy stock.</p>}
          {my.length === 0 && !loading && <p className="muted">You haven't listed anything yet. <Link to="/farm/listings/new">Create your first listing</Link> to start selling.</p>}
          {low.map((l) => <Link key={l.id} to={`/farm/listings/${l.id}`} className="alert alert-warn">{l.produce_name}: only {qty(l.availability!.available)} {l.quantity_unit} left. <b>Add stock</b></Link>)}
          <Link to="/farm/demand" className="btn btn-ghost btn-sm" style={{ justifySelf: "start" }}>See what buyers are asking for</Link>
        </section>
      </div>
    </div>
  );
}
