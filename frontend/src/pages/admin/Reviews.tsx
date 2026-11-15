import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { AdminReview, Envelope } from "../../api/types";
import { Pager, Stars } from "../../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../../components/Feedback";
import { useToast } from "../../components/Toasts";
import { shortDate, shortId } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";
import { ReasonDialog, useUrlState } from "./shared";

export default function Reviews() {
  const url = useUrlState();
  const toast = useToast();
  const res = useAsync<Envelope<AdminReview[]>>((s) => api.get<AdminReview[]>("/admin/reviews", { page: url.page, page_size: 10 }, s), [url.page]);
  const [target, setTarget] = useState<AdminReview | null>(null);
  const items = res.data?.data ?? [];
  return (
    <div className="wrap page" style={{ maxWidth: 820 }}>
      <div className="page-head"><h1>Review moderation</h1></div>
      <p className="muted small" style={{ marginBottom: 12 }}>Only buyers with a completed order can leave a review. Hide reviews that break the rules; hidden reviews no longer count towards a farmer's rating.</p>
      {res.error ? <ErrorState message={res.error} onRetry={res.reload} /> : res.loading && !res.data ? <Skeleton style={{ height: 200, borderRadius: 14 }} /> : items.length === 0 ? <EmptyState icon="⭐" title="No reviews yet" /> : (
        <div className="stack">{items.map((r) => (
          <div key={r.id} className="card card-pad stack" style={{ gap: 6 }}>
            <div className="row"><span className="wrap-row"><Stars value={r.rating} />{r.is_hidden && <span className="badge b-bad">Hidden</span>}</span><span className="muted small">{shortDate(r.created_at)} · order <Link to={`/orders/${r.order_id}`}>#{shortId(r.order_id)}</Link></span></div>
            <p>{r.comment || <span className="muted">No comment.</span>}</p>
            {r.is_hidden && r.moderation_reason && <p className="small">Reason: {r.moderation_reason}</p>}
            <div><button className={`btn btn-sm ${r.is_hidden ? "btn-ghost" : "btn-danger"}`} onClick={() => setTarget(r)}>{r.is_hidden ? "Restore" : "Hide"}</button></div>
          </div>))}</div>
      )}
      <Pager pagination={res.data?.pagination} onPage={(n) => url.set({ page: n > 1 ? String(n) : null })} />
      {target && (
        <ReasonDialog title={target.is_hidden ? "Restore review?" : "Hide review?"} confirmLabel={target.is_hidden ? "Restore review" : "Hide review"} danger={!target.is_hidden} required={!target.is_hidden}
          onConfirm={async (reason) => { await api.patch(`/admin/reviews/${target.id}/moderation`, { hidden: !target.is_hidden, reason }); toast.success(target.is_hidden ? "Review restored" : "Review hidden"); res.reload(); }}
          onClose={() => setTarget(null)} />
      )}
    </div>
  );
}
