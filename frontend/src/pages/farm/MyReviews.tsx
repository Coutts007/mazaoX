import { useState } from "react";
import { api } from "../../api/client";
import type { Envelope, Review } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { Pager, Stars } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { shortDate } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";

export default function MyReviews() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const res = useAsync<Envelope<Review[]>>((s) => api.get<Review[]>(`/farmers/${user!.id}/reviews`, { page, page_size: 10 }, s), [page]);
  const summary = (res.data as unknown as { summary?: { average_rating: number | null; review_count: number; distribution: Record<string, number> } } | null)?.summary;
  const items = res.data?.data ?? [];
  return (
    <div className="wrap page" style={{ maxWidth: 760 }}>
      <div className="page-head"><h1>My reviews</h1></div>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <Skeleton style={{ height: 160, borderRadius: 14 }} /> : (
        <>
          <div className="card card-pad row" style={{ marginBottom: 14 }}>
            <div><b className="price" style={{ fontSize: 32 }}>{summary?.average_rating ?? "–"}</b> <Stars value={summary?.average_rating ?? null} size={20} /><div className="muted small">{summary?.review_count ?? 0} verified-purchase reviews</div></div>
            <div className="dist">{[5, 4, 3, 2, 1].map((n) => { const c = summary?.distribution?.[String(n)] ?? 0; const t = summary?.review_count || 1; return <div key={n} className="row small"><span>{n}★</span><span className="bar"><i style={{ width: `${(c / t) * 100}%` }} /></span><span>{c}</span></div>; })}</div>
          </div>
          {items.length === 0 ? <EmptyState icon="⭐" title="No reviews yet">Buyers can review you after they receive an order.</EmptyState> : (
            <div className="stack">{items.map((r) => <div key={r.id} className="card card-pad stack" style={{ gap: 6 }}><div className="row"><Stars value={r.rating} /><span className="muted small">{shortDate(r.created_at)}</span></div>{r.comment ? <p>{r.comment}</p> : <p className="muted">No comment.</p>}</div>)}</div>
          )}
          <Pager pagination={res.data?.pagination} onPage={setPage} />
        </>
      )}
    </div>
  );
}
