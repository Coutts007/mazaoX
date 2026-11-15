import { Link } from "react-router-dom";
import { mediaUrl } from "../api/client";
import type { Listing } from "../api/types";
import { kes, qty } from "../lib/format";
import { ProduceArt } from "./ProduceArt";

export function StockBadge({ listing }: { listing: Listing }) {
  const a = listing.availability;
  if (!a) return null;
  const n = Number(a.available);
  if (!a.in_stock || n <= 0) return <span className="badge b-bad">Sold out</span>;
  if (n <= 20) return <span className="badge b-low">Only {qty(n)} {listing.quantity_unit} left</span>;
  return <span className="badge b-ok">{qty(n)} {listing.quantity_unit} available</span>;
}

/** Quality is always shown as the farmer's own claim unless an inspection says otherwise (never the case on the list). */
export function GradeBadge({ listing }: { listing: Listing }) {
  if (!listing.declared_grade) return null;
  return <span className="badge b-declared" title="This grade is declared by the farmer and has not been independently verified.">Farmer-declared: {listing.declared_grade.replace(/^Farmer-declared\s*/i, "")}</span>;
}

export function ListingCard({ listing }: { listing: Listing }) {
  const photo = listing.images[0];
  const place = [listing.locality, listing.county].filter(Boolean).join(", ");
  return (
    <Link to={`/listings/${listing.id}`} className="card card-hover lcard">
      <div className="photo">
        {photo ? <img src={mediaUrl(photo.url)} alt={listing.produce_name} loading="lazy" width={photo.width} height={photo.height} /> : <ProduceArt slug={listing.category.slug} />}
        <span className="tag"><StockBadge listing={listing} /></span>
      </div>
      <div className="body">
        <h3>{listing.produce_name}{listing.variety ? <span className="muted small"> · {listing.variety}</span> : null}</h3>
        <span className="muted small">{place || "Kenya"}</span>
        <span className="price">{kes(listing.price_per_unit)} <small>/ {listing.quantity_unit}</small></span>
        <GradeBadge listing={listing} />
      </div>
    </Link>
  );
}

export function ListingCardSkeleton() {
  return (
    <div className="card" aria-hidden="true">
      <div className="skeleton" style={{ aspectRatio: "4/3", borderRadius: 0 }} />
      <div className="body" style={{ padding: 14, display: "grid", gap: 8 }}>
        <div className="skeleton" style={{ height: 18, width: "70%" }} />
        <div className="skeleton" style={{ height: 14, width: "50%" }} />
        <div className="skeleton" style={{ height: 20, width: "40%" }} />
      </div>
    </div>
  );
}
