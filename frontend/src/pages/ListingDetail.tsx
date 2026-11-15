import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, mediaUrl } from "../api/client";
import type { Inspection, Listing, PublicFarmer, Review } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Quantity, Stars } from "../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../components/Feedback";
import { GradeBadge, StockBadge } from "../components/ListingCard";
import { Modal } from "../components/Modal";
import { ProduceArt } from "../components/ProduceArt";
import { useToast } from "../components/Toasts";
import { useCart } from "../cart/CartContext";
import { kes, qty, shortDate, timeAgo } from "../lib/format";
import { useAsync } from "../lib/useAsync";

function Gallery({ listing }: { listing: Listing }) {
  const [i, setI] = useState(0);
  const imgs = listing.images;
  if (!imgs.length) return <div className="card"><ProduceArt slug={listing.category.slug} size={96} /></div>;
  return (
    <div className="gallery">
      <div className="card gallery-main"><img src={mediaUrl(imgs[i].url)} alt={`${listing.produce_name}, photo ${i + 1} of ${imgs.length}`} width={imgs[i].width} height={imgs[i].height} /></div>
      {imgs.length > 1 && (
        <div className="gallery-thumbs">
          {imgs.map((m, n) => (
            <button key={m.id} className={n === i ? "on" : ""} onClick={() => setI(n)} aria-label={`Show photo ${n + 1}`} aria-pressed={n === i}><img src={mediaUrl(m.url)} alt="" /></button>
          ))}
        </div>
      )}
    </div>
  );
}

function FarmerCard({ farmerId }: { farmerId: string }) {
  const farmer = useAsync((s) => api.get<PublicFarmer>(`/farmers/${farmerId}`, undefined, s).then((r) => r.data), [farmerId]);
  const reviews = useAsync((s) => api.get<Review[]>(`/farmers/${farmerId}/reviews`, { page_size: 3 }, s), [farmerId]);
  if (farmer.loading) return <div className="card card-pad stack"><Skeleton style={{ height: 20, width: "60%" }} /><Skeleton style={{ height: 14 }} /></div>;
  if (!farmer.data) return null;
  const f = farmer.data;
  const summary = (reviews.data as unknown as { summary?: { average_rating: number | null; review_count: number } } | null)?.summary;
  const list = reviews.data?.data ?? [];
  return (
    <section className="card card-pad stack" aria-label="About the farmer">
      <div className="row">
        <div>
          <h3>{f.farm_name || f.full_name}</h3>
          <p className="muted small">{f.farm_name ? `${f.full_name} · ` : ""}{[f.locality, f.county].filter(Boolean).join(", ") || "Kenya"} · on MazaoX since {shortDate(f.member_since)}</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <Stars value={summary?.average_rating ?? null} />
          <div className="muted small">{summary?.review_count ? `${summary.average_rating} · ${summary.review_count} review${summary.review_count > 1 ? "s" : ""}` : "No reviews yet"}</div>
        </div>
      </div>
      {f.bio && <p>{f.bio}</p>}
      {list.length > 0 && (
        <div className="stack">
          {list.map((r) => (
            <div key={r.id} className="review">
              <div className="row"><Stars value={r.rating} size={14} /><span className="muted small">{timeAgo(r.created_at)}</span></div>
              {r.comment && <p>{r.comment}</p>}
            </div>
          ))}
          <span className="muted small">Reviews come only from buyers who received their order.</span>
        </div>
      )}
    </section>
  );
}

function Inspections({ listingId }: { listingId: string }) {
  const res = useAsync((s) => api.get<Inspection[]>(`/listings/${listingId}/inspections`, undefined, s).then((r) => r.data), [listingId]);
  const items = res.data ?? [];
  return (
    <section className="card card-pad stack" aria-label="Quality information">
      <h3>Quality</h3>
      <div className="alert alert-warn">The grade on this listing is <b>declared by the farmer</b>. It has not been independently verified.</div>
      {items.length === 0 ? (
        <p className="muted small">No independent inspection has been recorded for this listing.</p>
      ) : (
        items.map((i) => (
          <div key={i.id} className="alert alert-info">
            <b>✓ Independently inspected on {shortDate(i.inspected_on)}</b>: {i.result.replace(/_/g, " ")}{i.assessed_grade ? `, assessed grade ${i.assessed_grade}` : ""}.
            <div className="small">Scope: {i.scope}{i.notes ? ` · ${i.notes}` : ""}</div>
          </div>
        ))
      )}
    </section>
  );
}

export default function ListingDetail() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const cart = useCart();
  const toast = useToast();
  const navigate = useNavigate();
  const res = useAsync((s) => api.get<Listing>(`/listings/${id}`, undefined, s).then((r) => r.data), [id]);
  const [quantity, setQuantity] = useState(1);
  const [conflict, setConflict] = useState<null | "add" | "buy">(null);

  if (res.loading && !res.data) {
    return <div className="wrap page"><div className="detail"><Skeleton style={{ aspectRatio: "4/3" }} /><div className="stack"><Skeleton style={{ height: 32, width: "70%" }} /><Skeleton style={{ height: 24, width: "40%" }} /><Skeleton style={{ height: 120 }} /></div></div></div>;
  }
  if (res.error) {
    const notFound = res.error.toLowerCase().includes("not found");
    return <div className="wrap">{notFound ? <EmptyState icon="🧺" title="This listing isn't available" action={{ to: "/browse", label: "Browse produce" }}>It may have been sold out, deactivated or removed.</EmptyState> : <ErrorState message={res.error} onRetry={res.reload} />}</div>;
  }
  const l = res.data!;
  const available = l.availability ? Number(l.availability.available) : null;
  const soldOut = l.availability ? !l.availability.in_stock || Number(l.availability.available) <= 0 : false;
  const canBuy = !user || user.role === "buyer";
  const mine = user?.role === "farmer" && user.id === l.farmer_id;
  const place = [l.locality, l.county].filter(Boolean).join(", ");

  const addToCart = (go: boolean) => {
    if (cart.add(l, quantity) === "conflict") return setConflict(go ? "buy" : "add");
    if (go) navigate("/cart");
    else toast.success(`${quantity} ${l.quantity_unit} of ${l.produce_name} added to your cart`);
  };

  return (
    <div className="wrap page">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/browse">Browse</Link> › <Link to={`/browse?category_id=${l.category.id}`}>{l.category.name}</Link> › <span>{l.produce_name}</span></nav>
      <div className="detail">
        <Gallery listing={l} />
        <div className="stack">
          <div>
            <h1>{l.produce_name}{l.variety ? <span className="muted"> · {l.variety}</span> : null}</h1>
            <p className="muted">📍 {place || "Kenya"}{l.harvest_date ? ` · Harvested ${shortDate(l.harvest_date)}` : ""}</p>
          </div>
          <div className="price-big">{kes(l.price_per_unit)} <small>per {l.quantity_unit}</small></div>
          <div className="wrap-row"><StockBadge listing={l} /><GradeBadge listing={l} /></div>
          {l.description && <p>{l.description}</p>}

          <div className="card card-pad stack buybox">
            {mine ? (
              <div className="alert alert-info">This is your listing. <Link to={`/farm/listings/${l.id}`}>Manage it</Link></div>
            ) : !canBuy ? (
              <div className="alert alert-info">You're logged in as a {user?.role}. Use a buyer account to place orders.</div>
            ) : soldOut ? (
              <div className="alert alert-warn">Sold out right now. <Link to="/requests">Post a request</Link> and farmers can reach out.</div>
            ) : (
              <>
                <div className="row">
                  <Quantity value={quantity} max={available} onChange={setQuantity} label={`Quantity in ${l.quantity_unit}`} />
                  <div style={{ textAlign: "right" }}>
                    <div className="muted small">Estimated total</div>
                    <b className="price">{kes(Number(l.price_per_unit) * quantity)}</b>
                  </div>
                </div>
                {available !== null && quantity >= Math.floor(available) && <p className="muted small">That's everything available ({qty(available)} {l.quantity_unit}).</p>}
                <div className="wrap-row">
                  <button className="btn btn-primary grow" onClick={() => addToCart(false)}>🛒 Add to cart</button>
                  <button className="btn btn-accent grow" onClick={() => addToCart(true)}>Buy now</button>
                </div>
                <p className="muted small">The final price is confirmed by the server when you place the order. Stock is held for 15 minutes while you pay.</p>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="detail-more">
        <Inspections listingId={l.id} />
        <FarmerCard farmerId={l.farmer_id} />
      </div>

      {conflict && (
        <Modal title="Start a new cart?" onClose={() => setConflict(null)} footer={<><button className="btn btn-ghost" onClick={() => setConflict(null)}>Keep my cart</button><button className="btn btn-primary" onClick={() => { cart.replaceWith(l, quantity); const go = conflict === "buy"; setConflict(null); go ? navigate("/cart") : toast.success("New cart started"); }}>Start new cart</button></>}>
          <p>Each order is from <b>one farmer</b>. Your cart already has produce from a different farmer. Do you want to replace it with this item?</p>
        </Modal>
      )}
    </div>
  );
}

