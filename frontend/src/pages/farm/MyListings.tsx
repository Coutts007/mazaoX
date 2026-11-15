import { Link } from "react-router-dom";
import { useState } from "react";
import { api, errorMessage, mediaUrl } from "../../api/client";
import type { Envelope, Listing } from "../../api/types";
import { Pager } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { ProduceArt } from "../../components/ProduceArt";
import { useToast } from "../../components/Toasts";
import { kes, qty } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";

export default function MyListings() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const res = useAsync<Envelope<Listing[]>>((s) => api.get<Listing[]>("/listings", { mine: "true", page, page_size: 12 }, s), [page]);
  const items = res.data?.data ?? [];
  async function toggle(l: Listing) {
    try {
      await api.post(`/listings/${l.id}/${l.status === "active" ? "deactivate" : "activate"}`);
      toast.success(l.status === "active" ? "Listing hidden from buyers" : "Listing is live again");
      res.reload();
    } catch (e) { toast.error(errorMessage(e)); }
  }
  return (
    <div className="wrap page">
      <div className="page-head"><div><h1>My listings</h1><p className="muted">What buyers see, and how much you have left.</p></div><Link className="btn btn-primary" to="/farm/listings/new">+ New listing</Link></div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <div className="stack">{[0, 1, 2].map((i) => <Skeleton key={i} style={{ height: 96, borderRadius: 14 }} />)}</div> : items.length === 0 ? (
        <EmptyState icon="🧺" title="No listings yet" action={{ to: "/farm/listings/new", label: "Create your first listing" }}>List what you have harvested and buyers across Kenya can find it.</EmptyState>
      ) : (
        <div className="stack">
          {items.map((l) => {
            const a = l.availability ? Number(l.availability.available) : null;
            return (
              <div key={l.id} className="card card-pad my-listing">
                <Link to={`/farm/listings/${l.id}`} className="cart-thumb">{l.images[0] ? <img src={mediaUrl(l.images[0].url)} alt="" /> : <ProduceArt slug={l.category.slug} size={30} />}</Link>
                <div className="grow stack" style={{ gap: 6 }}>
                  <div className="row"><Link to={`/farm/listings/${l.id}`}><b>{l.produce_name}</b></Link>
                    <span>{l.moderation_hidden ? <span className="badge b-bad">Hidden by admin</span> : <span className={`badge ${l.status === "active" ? "b-ok" : "b-off"}`}>{l.status === "active" ? "Live" : "Not listed"}</span>}</span></div>
                  <span className="muted small">{kes(l.price_per_unit)} / {l.quantity_unit} · {a === null ? "stock unknown" : a <= 0 ? "out of stock" : `${qty(a)} ${l.quantity_unit} available`}</span>
                  {l.moderation_hidden && l.moderation_reason && <div className="alert alert-error small">Reason: {l.moderation_reason}</div>}
                  <div className="wrap-row">
                    <Link className="btn btn-ghost btn-sm" to={`/farm/listings/${l.id}`}>Edit &amp; stock</Link>
                    <button className="btn btn-text btn-sm" onClick={() => toggle(l)}>{l.status === "active" ? "Take offline" : "Put live"}</button>
                    <Link className="btn btn-text btn-sm" to={`/listings/${l.id}`}>View as buyer</Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <Pager pagination={res.data?.pagination} onPage={setPage} />
    </div>
  );
}
