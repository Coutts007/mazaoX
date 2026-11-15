import { useEffect, useState } from "react";
import type { Pagination as P } from "../api/types";

export function Stars({ value, size = 16 }: { value: number | null; size?: number }) {
  const v = value ?? 0;
  return (
    <span className="stars" style={{ fontSize: size }} role="img" aria-label={value === null ? "No ratings yet" : `${v.toFixed(1)} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((n) => <span key={n} className={n <= Math.round(v) ? "on" : ""}>★</span>)}
    </span>
  );
}

export function StarPicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div className="star-picker" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button type="button" key={n} role="radio" aria-checked={value === n} aria-label={`${n} star${n > 1 ? "s" : ""}`} className={n <= value ? "on" : ""} onClick={() => onChange(n)}>★</button>
      ))}
    </div>
  );
}

export function Pager({ pagination, onPage }: { pagination?: P; onPage: (n: number) => void }) {
  if (!pagination || pagination.total_pages <= 1) return null;
  const { page, total_pages } = pagination;
  const pages = new Set([1, total_pages, page - 1, page, page + 1]);
  const list = [...pages].filter((n) => n >= 1 && n <= total_pages).sort((a, b) => a - b);
  return (
    <nav className="pager" aria-label="Pagination">
      <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>← Previous</button>
      <span className="pager-pages">
        {list.map((n, i) => (
          <span key={n}>
            {i > 0 && n - list[i - 1] > 1 && <span className="muted">…</span>}
            <button className={`chip ${n === page ? "on" : ""}`} aria-current={n === page ? "page" : undefined} onClick={() => onPage(n)}>{n}</button>
          </span>
        ))}
      </span>
      <button className="btn btn-ghost btn-sm" disabled={page >= total_pages} onClick={() => onPage(page + 1)}>Next →</button>
    </nav>
  );
}

/** Counts down to a server-provided deadline (never a client-side guess). */
export function Countdown({ until, onDone }: { until: string; onDone?: () => void }) {
  const [left, setLeft] = useState(() => Math.max(0, new Date(until).getTime() - Date.now()));
  useEffect(() => {
    const tick = () => {
      const ms = Math.max(0, new Date(until).getTime() - Date.now());
      setLeft(ms);
      if (ms === 0) onDone?.();
    };
    tick();
    const t = window.setInterval(tick, 1000);
    return () => window.clearInterval(t);
  }, [until, onDone]);
  const m = Math.floor(left / 60000);
  const s = Math.floor((left % 60000) / 1000);
  return <b className="mono">{String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}</b>;
}

export function Quantity({ value, min = 1, max, onChange, label = "Quantity" }: { value: number; min?: number; max?: number | null; onChange: (n: number) => void; label?: string }) {
  const clamp = (n: number) => Math.max(min, max != null ? Math.min(n, Math.floor(max)) : n);
  return (
    <div className="qty" role="group" aria-label={label}>
      <button type="button" onClick={() => onChange(clamp(value - 1))} disabled={value <= min} aria-label="Decrease quantity">−</button>
      <input
        inputMode="numeric"
        aria-label={label}
        value={value}
        onChange={(e) => { const n = parseInt(e.target.value.replace(/\D/g, ""), 10); onChange(Number.isNaN(n) ? min : clamp(n)); }}
      />
      <button type="button" onClick={() => onChange(clamp(value + 1))} disabled={max != null && value >= Math.floor(max)} aria-label="Increase quantity">+</button>
    </div>
  );
}
