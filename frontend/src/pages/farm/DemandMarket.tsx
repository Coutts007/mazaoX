import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { DemandRequest, Envelope } from "../../api/types";
import { Pager } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { COUNTIES } from "../../lib/constants";
import { kes, qty, shortDate } from "../../lib/format";
import { useAsync, useDebounced } from "../../lib/useAsync";

export default function DemandMarket() {
  const [produce, setProduce] = useState("");
  const [county, setCounty] = useState("");
  const [page, setPage] = useState(1);
  const dp = useDebounced(produce, 350);
  const res = useAsync<Envelope<DemandRequest[]>>((s) => api.get<DemandRequest[]>("/demand-requests/market", { produce: dp, county, page, page_size: 12 }, s), [dp, county, page]);
  const items = res.data?.data ?? [];
  return (
    <div className="wrap page">
      <div className="page-head"><div><h1>What buyers want</h1><p className="muted">Open requests from buyers. Names and contacts are never shown.</p></div><Link to="/farm/listings/new" className="btn btn-accent">List my produce</Link></div>
      <div className="wrap-row" style={{ marginBottom: 14 }}>
        <input className="input" style={{ maxWidth: 280 }} placeholder="Filter by produce" aria-label="Filter by produce" value={produce} onChange={(e) => { setProduce(e.target.value); setPage(1); }} />
        <select className="select" style={{ maxWidth: 220 }} aria-label="County" value={county} onChange={(e) => { setCounty(e.target.value); setPage(1); }}><option value="">All counties</option>{COUNTIES.map((c) => <option key={c}>{c}</option>)}</select>
      </div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <Skeleton style={{ height: 120, borderRadius: 14 }} /> : items.length === 0 ? <EmptyState icon="📣" title="No open requests match">Check back later, or clear the filters.</EmptyState> : (
        <div className="lgrid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))" }}>
          {items.map((r) => (
            <div key={r.id} className="card card-pad stack">
              <b className="price">{qty(r.quantity)} {r.quantity_unit}</b>
              <h3>{r.produce_name}</h3>
              <p className="muted small">{r.county} · needed by {shortDate(r.required_by)}</p>
              {r.target_price_per_unit && <span className="badge b-ok" style={{ justifySelf: "start" }}>Target {kes(r.target_price_per_unit)} / {r.quantity_unit}</span>}
            </div>
          ))}
        </div>
      )}
      <Pager pagination={res.data?.pagination} onPage={setPage} />
    </div>
  );
}
