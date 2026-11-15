import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Category, Listing } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorState } from "../components/Feedback";
import { ListingCard, ListingCardSkeleton } from "../components/ListingCard";
import { artFor } from "../components/ProduceArt";
import { useAsync } from "../lib/useAsync";

export default function Home() {
  const { user } = useAuth();
  const cats = useAsync((s) => api.get<Category[]>("/categories", undefined, s).then((r) => r.data), []);
  const fresh = useAsync((s) => api.get<Listing[]>("/listings", { page_size: 8, ordering: "newest" }, s).then((r) => r.data), []);

  return (
    <div className="wrap">
      <section className="hero">
        <div>
          <span className="eyebrow">Straight from Kenyan farms</span>
          <h1>Fresh produce, <em>fair prices</em>, from farmers you can see.</h1>
          <p className="lead">Browse what farmers harvested today, order what you need and follow it all the way to your door. Every listing shows who grew it and where.</p>
          <div className="wrap-row">
            <Link className="btn btn-accent" to="/browse">Shop fresh produce</Link>
            {!user && <Link className="btn btn-ghost" to="/register?role=farmer">I'm a farmer</Link>}
            {user?.role === "farmer" && <Link className="btn btn-ghost" to="/farm">Go to my farm</Link>}
          </div>
        </div>
        <div className="hero-art" aria-hidden="true"><span>🍅</span><span>🥬</span><span>🌽</span><span>🥔</span><span>🧅</span><span>🌱</span></div>
      </section>

      <section className="trust" aria-label="Why MazaoX">
        <div><b>👩🏾‍🌾 Know your farmer</b><span className="muted small">Public farm profiles with real reviews.</span></div>
        <div><b>📦 Stock you can trust</b><span className="muted small">Your order is held for 15 minutes while you pay.</span></div>
        <div><b>🔎 Honest quality</b><span className="muted small">Farmer-declared grades are never passed off as verified.</span></div>
        <div><b>⭐ Verified reviews</b><span className="muted small">Only buyers who received their order can review.</span></div>
      </section>

      <div className="section-title"><h2>Shop by category</h2><Link to="/browse">All produce →</Link></div>
      <div className="cats" role="list">
        {cats.loading && Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton" style={{ width: 68, height: 90, flex: "none" }} />)}
        {cats.data?.map((c) => (
          <Link role="listitem" key={c.id} className="cat" to={`/browse?category_id=${c.id}`}>
            <i aria-hidden="true">{artFor(c.slug).emoji}</i>{c.name}
          </Link>
        ))}
      </div>

      <div className="section-title"><h2>Fresh from the farm</h2><Link to="/browse">See all →</Link></div>
      {fresh.error ? (
        <ErrorState message={fresh.error} onRetry={fresh.reload} />
      ) : (
        <div className="lgrid">
          {fresh.loading ? Array.from({ length: 4 }).map((_, i) => <ListingCardSkeleton key={i} />) : fresh.data?.map((l) => <ListingCard key={l.id} listing={l} />)}
        </div>
      )}
      {!fresh.loading && !fresh.error && fresh.data?.length === 0 && (
        <p className="muted" style={{ textAlign: "center", padding: 24 }}>No produce listed yet. Check back soon.</p>
      )}

      <div className="section-title"><h2>How it works</h2></div>
      <div className="how">
        <div className="step"><b>1</b><h3>Find</h3><p className="muted">Search by produce, county or price. Filters stay in the link so you can share a search.</p></div>
        <div className="step"><b>2</b><h3>Order &amp; pay</h3><p className="muted">We reserve your stock, you complete a (demo) payment within 15 minutes.</p></div>
        <div className="step"><b>3</b><h3>Receive &amp; review</h3><p className="muted">Follow delivery updates, report a problem if needed, then rate the farmer.</p></div>
      </div>

      {!user && (
        <div className="cta-band">
          <div><h2>Grow with MazaoX</h2><p>List your harvest in minutes and reach buyers across Kenya.</p></div>
          <Link className="btn btn-accent" to="/register?role=farmer">Start selling</Link>
        </div>
      )}
    </div>
  );
}
