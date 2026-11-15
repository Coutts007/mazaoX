import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Category, Envelope, Listing } from "../api/types";
import { Pager } from "../components/Bits";
import { EmptyState, ErrorState } from "../components/Feedback";
import { ListingCard, ListingCardSkeleton } from "../components/ListingCard";
import { Modal } from "../components/Modal";
import { COUNTIES } from "../lib/constants";
import { useAsync, useDebounced } from "../lib/useAsync";

const PAGE_SIZE = 12;
const ORDERINGS = [
  { value: "newest", label: "Newest first" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "harvest_newest", label: "Freshest harvest" },
];
const FILTER_KEYS = ["category_id", "county", "min_price", "max_price", "min_quantity", "ordering"] as const;

interface FilterProps {
  params: URLSearchParams;
  set: (patch: Record<string, string | null>) => void;
  categories: Category[];
}

function Filters({ params, set, categories }: FilterProps) {
  const [min, setMin] = useState(params.get("min_price") ?? "");
  const [max, setMax] = useState(params.get("max_price") ?? "");
  useEffect(() => {
    setMin(params.get("min_price") ?? "");
    setMax(params.get("max_price") ?? "");
  }, [params]);
  const commitPrice = () => set({ min_price: min || null, max_price: max || null });
  return (
    <div className="filters stack">
      <div className="field">
        <label>Category</label>
        <div className="scroll-x" style={{ flexWrap: "wrap" }}>
          <button className={`chip ${!params.get("category_id") ? "on" : ""}`} onClick={() => set({ category_id: null })}>All</button>
          {categories.map((c) => (
            <button key={c.id} className={`chip ${params.get("category_id") === c.id ? "on" : ""}`} onClick={() => set({ category_id: c.id })}>{c.name}</button>
          ))}
        </div>
      </div>
      <div className="field">
        <label htmlFor="f-county">County</label>
        <select id="f-county" className="select" value={params.get("county") ?? ""} onChange={(e) => set({ county: e.target.value || null })}>
          <option value="">All counties</option>
          {COUNTIES.map((c) => <option key={c}>{c}</option>)}
        </select>
      </div>
      <div className="field">
        <label>Price per unit (KES)</label>
        <div className="wrap-row" style={{ flexWrap: "nowrap" }}>
          <input className="input" inputMode="decimal" placeholder="Min" aria-label="Minimum price" value={min} onChange={(e) => setMin(e.target.value.replace(/[^\d.]/g, ""))} onBlur={commitPrice} onKeyDown={(e) => e.key === "Enter" && commitPrice()} />
          <span>–</span>
          <input className="input" inputMode="decimal" placeholder="Max" aria-label="Maximum price" value={max} onChange={(e) => setMax(e.target.value.replace(/[^\d.]/g, ""))} onBlur={commitPrice} onKeyDown={(e) => e.key === "Enter" && commitPrice()} />
        </div>
      </div>
      <label className="check">
        <input type="checkbox" checked={!!params.get("min_quantity")} onChange={(e) => set({ min_quantity: e.target.checked ? "1" : null })} /> In stock now
      </label>
      <div className="field">
        <label htmlFor="f-sort">Sort by</label>
        <select id="f-sort" className="select" value={params.get("ordering") ?? "newest"} onChange={(e) => set({ ordering: e.target.value === "newest" ? null : e.target.value })}>
          {ORDERINGS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
    </div>
  );
}

export default function Browse() {
  const [params, setParams] = useSearchParams();
  const categories = useAsync((s) => api.get<Category[]>("/categories", undefined, s).then((r) => r.data), []);
  const [q, setQ] = useState(params.get("q") ?? "");
  const debouncedQ = useDebounced(q, 350);
  const [sheet, setSheet] = useState(false);

  const set = (patch: Record<string, string | null>, keepPage = false) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) (v ? next.set(k, v) : next.delete(k));
    if (!keepPage) next.delete("page");
    setParams(next, { replace: true });
  };

  // keep the URL in step with the (debounced) search box
  useEffect(() => {
    if ((params.get("q") ?? "") !== debouncedQ.trim()) set({ q: debouncedQ.trim() || null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);
  // and the box in step with the URL (e.g. header search, back button)
  const urlQ = params.get("q") ?? "";
  useEffect(() => {
    setQ((cur) => (cur.trim() === urlQ ? cur : urlQ));
  }, [urlQ]);

  const query = useMemo(() => {
    const out: Record<string, string> = { page_size: String(PAGE_SIZE) };
    for (const k of ["q", "page", ...FILTER_KEYS]) {
      const v = params.get(k);
      if (v) out[k] = v;
    }
    return out;
  }, [params]);

  const result = useAsync<Envelope<Listing[]>>((s) => api.get<Listing[]>("/listings", query, s), [JSON.stringify(query)]);
  const items = result.data?.data ?? [];
  const total = result.data?.pagination?.total_items ?? 0;

  const activeFilters: { key: string; label: string }[] = [];
  const catName = (id: string) => categories.data?.find((c) => c.id === id)?.name ?? "Category";
  if (params.get("q")) activeFilters.push({ key: "q", label: `“${params.get("q")}”` });
  if (params.get("category_id")) activeFilters.push({ key: "category_id", label: catName(params.get("category_id")!) });
  if (params.get("county")) activeFilters.push({ key: "county", label: params.get("county")! });
  if (params.get("min_price") || params.get("max_price")) activeFilters.push({ key: "price", label: `KES ${params.get("min_price") || 0} – ${params.get("max_price") || "any"}` });
  if (params.get("min_quantity")) activeFilters.push({ key: "min_quantity", label: "In stock now" });

  const clear = (key: string) => {
    if (key === "price") set({ min_price: null, max_price: null });
    else {
      set({ [key]: null });
      if (key === "q") setQ("");
    }
  };
  const clearAll = () => { setQ(""); setParams(new URLSearchParams(), { replace: true }); };

  const filterProps = { params, set, categories: categories.data ?? [] };

  return (
    <div className="wrap page">
      <div className="page-head">
        <div>
          <h1>Fresh produce</h1>
          <p className="muted" aria-live="polite">{result.loading && !result.data ? "Searching…" : `${total} ${total === 1 ? "listing" : "listings"}${activeFilters.length ? " match your search" : " available"}`}</p>
        </div>
        <button className="btn btn-ghost btn-sm filters-btn" onClick={() => setSheet(true)}>Filters{activeFilters.filter((f) => f.key !== "q").length ? ` (${activeFilters.filter((f) => f.key !== "q").length})` : ""}</button>
      </div>

      <div className="search-big">
        <input className="input" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tomatoes, kale, maize…" aria-label="Search produce" />
      </div>

      {activeFilters.length > 0 && (
        <div className="scroll-x" aria-label="Active filters">
          {activeFilters.map((f) => <button key={f.key} className="chip chip-x" onClick={() => clear(f.key)} aria-label={`Remove filter ${f.label}`}>{f.label}</button>)}
          <button className="btn btn-text btn-sm" onClick={clearAll}>Clear all</button>
        </div>
      )}

      <div className="browse">
        <aside className="card card-pad browse-side" aria-label="Filters"><Filters {...filterProps} /></aside>
        <section aria-busy={result.loading}>
          {result.error ? (
            <ErrorState message={result.error} onRetry={result.reload} />
          ) : result.loading && !result.data ? (
            <div className="lgrid">{Array.from({ length: 8 }).map((_, i) => <ListingCardSkeleton key={i} />)}</div>
          ) : items.length === 0 ? (
            <EmptyState icon="🔎" title="Nothing matches yet">Try a different spelling, remove a filter, or post a request so farmers can find you.</EmptyState>
          ) : (
            <div className="lgrid results" style={{ opacity: result.loading ? 0.55 : 1 }}>{items.map((l) => <ListingCard key={l.id} listing={l} />)}</div>
          )}
          <Pager pagination={result.data?.pagination} onPage={(n) => { set({ page: n > 1 ? String(n) : null }, true); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
        </section>
      </div>

      {sheet && (
        <Modal title="Filters" onClose={() => setSheet(false)} footer={<><button className="btn btn-text" onClick={clearAll}>Clear all</button><button className="btn btn-primary" onClick={() => setSheet(false)}>Show {total} results</button></>}>
          <Filters {...filterProps} />
        </Modal>
      )}
    </div>
  );
}
