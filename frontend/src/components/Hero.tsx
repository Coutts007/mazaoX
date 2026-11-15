import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { mediaUrl } from "../api/client";
import type { Category, Listing } from "../api/types";
import { SITE_IMAGES } from "../config/images";
import { kes } from "../lib/format";
import { ProduceArt } from "./ProduceArt";
import { useBackground } from "./SiteImage";

/**
 * Home hero. The background is your photo (`SITE_IMAGES.hero`); until you add one it is a plain dark green.
 * The text card floats on top of it.
 */
export function Hero({ categories, listings, role }: { categories: Category[] | null; listings: Listing[] | null; role?: string }) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const bg = useBackground(SITE_IMAGES.hero);
  function submit(e: FormEvent) {
    e.preventDefault();
    navigate(`/browse${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ""}`);
  }
  const latest = (listings ?? []).slice(0, 3);
  return (
    <section className="hero" style={bg} aria-label="Welcome">
      <div className="wrap hero-inner">
        <div className="hero-card">
          <p className="kicker">Straight from Kenyan farms</p>
          <h1>Fresh produce, fair prices, from farmers you can see.</h1>
          <p className="lead">Browse what farmers have harvested, order what you need and follow it to your door. Every listing shows who grew it and where.</p>
          <form className="hero-search" role="search" onSubmit={submit}>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tomatoes, kale, maize…" aria-label="Search produce" />
            <button className="btn btn-accent">Search</button>
          </form>
          {categories && categories.length > 0 && (
            <p className="hero-links">Popular: {categories.slice(0, 5).map((c, i) => <span key={c.id}>{i > 0 && ", "}<Link to={`/browse?category_id=${c.id}`}>{c.name}</Link></span>)}</p>
          )}
          <div className="wrap-row">
            {!role && <Link className="btn btn-ghost" to="/register?role=farmer">I'm a farmer</Link>}
            {role === "farmer" && <Link className="btn btn-ghost" to="/farm">Go to my farm</Link>}
          </div>
        </div>
        {latest.length > 0 && (
          <aside className="hero-latest" aria-label="Recently listed">
            <h2>Recently listed</h2>
            {latest.map((l) => (
              <Link key={l.id} to={`/listings/${l.id}`} className="mini">
                <span className="mini-photo">{l.images[0] ? <img src={mediaUrl(l.images[0].url)} alt="" loading="lazy" /> : <ProduceArt slug={l.category.slug} name={l.produce_name} />}</span>
                <span><b>{l.produce_name}</b><small>{l.county} · {kes(l.price_per_unit)} / {l.quantity_unit}</small></span>
              </Link>
            ))}
            <Link to="/browse" className="all">See all produce →</Link>
          </aside>
        )}
      </div>
    </section>
  );
}
