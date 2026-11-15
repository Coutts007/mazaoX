import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { mediaUrl } from "../api/client";
import type { Category, Listing } from "../api/types";
import { kes } from "../lib/format";
import { CountUp } from "./Reveal";
import { artFor, ProduceArt } from "./ProduceArt";

const WORDS = ["tomatoes", "kale", "maize", "onions", "potatoes"];

/** Layered, animated landscape. Purely decorative, so it is hidden from assistive tech. */
function Scenery() {
  return (
    <div className="hero-bg" aria-hidden="true">
      <div className="sun" />
      <div className="blob b1" /><div className="blob b2" /><div className="blob b3" />
      <svg className="hills h3" viewBox="0 0 1440 320" preserveAspectRatio="none"><path d="M0 190c180-60 330-70 520-20s330 80 520 20 290-70 400-30v160H0z" /></svg>
      <svg className="hills h2" viewBox="0 0 1440 320" preserveAspectRatio="none"><path d="M0 220c200-70 380-40 560 10s360 60 540-10 220-50 340-20v120H0z" /></svg>
      <svg className="hills h1" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path d="M0 260c220-50 420-20 640 20s420 30 800-30v70H0z" />
        <g className="rows">{Array.from({ length: 9 }).map((_, i) => <path key={i} d={`M${i * 180 - 40} 320 Q${i * 180 + 30} 285 ${i * 180 + 120} 262`} />)}</g>
      </svg>
      {["🌿", "🍃", "🌾", "🍃", "🌿", "🌾"].map((e, i) => <span key={i} className={`leaf l${i + 1}`}>{e}</span>)}
      <div className="grain" />
    </div>
  );
}

function FloatCard({ listing, index }: { listing: Listing; index: number }) {
  const photo = listing.images[0];
  return (
    <Link to={`/listings/${listing.id}`} className={`fcard fc${index + 1}`}>
      <div className="fphoto">{photo ? <img src={mediaUrl(photo.url)} alt="" loading="lazy" /> : <ProduceArt slug={listing.category.slug} size={34} />}</div>
      <div><b>{listing.produce_name}</b><span>{listing.county} · {kes(listing.price_per_unit)}/{listing.quantity_unit}</span></div>
    </Link>
  );
}

export function Hero({ categories, listings, role }: { categories: Category[] | null; listings: Listing[] | null; role?: string }) {
  const navigate = useNavigate();
  const ref = useRef<HTMLElement>(null);
  const [q, setQ] = useState("");
  const [w, setW] = useState(0);

  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => setW((x) => (x + 1) % WORDS.length), 2400);
    return () => clearInterval(t);
  }, []);

  // Pointer parallax: writes CSS variables directly so the page does not re-render on every move.
  function onMove(e: React.PointerEvent) {
    const el = ref.current;
    if (!el || e.pointerType === "touch" || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", String(((e.clientX - r.left) / r.width - 0.5).toFixed(3)));
    el.style.setProperty("--my", String(((e.clientY - r.top) / r.height - 0.5).toFixed(3)));
  }
  function submit(e: FormEvent) {
    e.preventDefault();
    navigate(`/browse${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ""}`);
  }
  const floats = (listings ?? []).slice(0, 3);
  return (
    <section className="hero2" ref={ref} onPointerMove={onMove} aria-label="Welcome">
      <Scenery />
      <div className="wrap hero-inner">
        <div className="hero-card">
          <span className="eyebrow">🇰🇪 Straight from Kenyan farms</span>
          <h1>Fresh <span className="swap" aria-hidden="true"><em key={w}>{WORDS[w]}</em></span><span className="sr-only">produce</span>, fair prices, from farmers you can see.</h1>
          <p className="lead">Browse what farmers harvested, order what you need and follow it all the way to your door. Every listing shows who grew it and where.</p>
          <form className="hero-search" role="search" onSubmit={submit}>
            <span aria-hidden="true">🔍</span>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tomatoes, kale, maize…" aria-label="Search produce" />
            <button className="btn btn-accent">Search</button>
          </form>
          <div className="hero-chips" aria-label="Popular categories">
            {(categories ?? []).slice(0, 5).map((c) => <Link key={c.id} to={`/browse?category_id=${c.id}`} className="chip-x2"><i aria-hidden="true">{artFor(c.slug).emoji}</i>{c.name}</Link>)}
          </div>
          <div className="wrap-row">
            {!role && <Link className="btn btn-ghost" to="/register?role=farmer">I'm a farmer</Link>}
            {role === "farmer" && <Link className="btn btn-ghost" to="/farm">Go to my farm</Link>}
            <Link className="btn btn-text" to="/browse">Browse everything →</Link>
          </div>
          <dl className="hero-stats">
            <div><dt>Counties served</dt><dd><CountUp to={47} /></dd></div>
            <div><dt>Minute stock hold</dt><dd><CountUp to={15} /></dd></div>
            <div><dt>Produce categories</dt><dd><CountUp to={categories?.length ?? 0} /></dd></div>
          </dl>
        </div>
        <div className="hero-float" aria-label="Fresh listings">
          {floats.length > 0
            ? floats.map((l, i) => <FloatCard key={l.id} listing={l} index={i} />)
            : <div className="hero-art" aria-hidden="true"><span>🍅</span><span>🥬</span><span>🌽</span></div>}
        </div>
      </div>
    </section>
  );
}
