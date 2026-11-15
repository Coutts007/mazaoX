import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, errorMessage } from "../api/client";
import type { Delivery, Issue, Order, OrderHistoryItem, PaymentAttempt, PublicFarmer } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Countdown, StarPicker } from "../components/Bits";
import { EmptyState, ErrorState, Skeleton } from "../components/Feedback";
import { SelectField, TextAreaField } from "../components/Field";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toasts";
import { ORDER_STATUS_BADGE, ORDER_STATUS_LABEL } from "../lib/constants";
import { dateTime, kes, qty, shortId } from "../lib/format";
import { useAsync } from "../lib/useAsync";

function Timeline({ order, delivery }: { order: Order; delivery: Delivery | null }) {
  const s = order.status;
  if (s === "cancelled" || s === "expired") {
    return <div className="timeline"><span className="done">Placed</span><span className="bad">{ORDER_STATUS_LABEL[s]}</span></div>;
  }
  const paid = s === "paid" || s === "completed";
  const dispatched = delivery?.status === "dispatched" || delivery?.status === "delivered" || s === "completed";
  return (
    <div className="timeline" aria-label="Order progress">
      <span className="done">Placed</span>
      <span className={paid ? "done" : "now"}>{paid ? "Paid" : "Awaiting payment"}</span>
      <span className={s === "completed" ? "done" : dispatched ? "done" : paid ? "now" : ""}>{dispatched ? "On its way / ready" : "Preparing"}</span>
      <span className={s === "completed" ? "done" : ""}>{order.delivery_method === "delivery" ? "Delivered" : "Collected"}</span>
    </div>
  );
}

function PayPanel({ order, onChanged }: { order: Order; onChanged: () => void }) {
  const toast = useToast();
  const [attempt, setAttempt] = useState<PaymentAttempt | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy("start"); setError(null);
    try { setAttempt((await api.post<PaymentAttempt>(`/orders/${order.id}/payment-simulation`)).data); }
    catch (e) { setError(errorMessage(e)); onChanged(); }
    finally { setBusy(null); }
  }
  async function finish(outcome: "success" | "failure") {
    if (!attempt) return;
    setBusy(outcome); setError(null);
    try {
      const r = await api.post<PaymentAttempt>(`/payments/simulations/${attempt.id}/complete`, { outcome });
      setAttempt(r.data);
      if (r.data.status === "succeeded") toast.success("Payment received. The farmer has been told to prepare your order.");
      else toast.error("The payment did not go through. You can try again while the order is open.");
      if (r.data.status === "failed") setAttempt(null);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(null); onChanged(); } // always re-read the order: the server decides its status
  }

  return (
    <section className="card card-pad stack pay" aria-label="Payment">
      <div className="row"><h3>Pay for this order</h3>{order.payment_due_by && <span>Time left <Countdown until={order.payment_due_by} onDone={onChanged} /></span>}</div>
      <div className="demo"><b>Demo payment.</b> No real money moves, and we never ask for an M-Pesa PIN or card details.</div>
      <div className="row"><span>Amount</span><b className="price">{kes(order.total_amount)}</b></div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {!attempt ? (
        <button className="btn btn-primary btn-block" onClick={start} disabled={!!busy}>{busy === "start" ? <span className="spinner" /> : null}Pay with M-Pesa (demo)</button>
      ) : (
        <div className="stack">
          <p className="muted small">Payment started. In this prototype you choose what the simulated payment provider reports back:</p>
          <button className="btn btn-primary btn-block" onClick={() => finish("success")} disabled={!!busy}>{busy === "success" ? <span className="spinner" /> : null}✓ Simulate successful payment</button>
          <button className="btn btn-ghost btn-block" onClick={() => finish("failure")} disabled={!!busy}>{busy === "failure" ? <span className="spinner" /> : null}✕ Simulate failed payment</button>
        </div>
      )}
    </section>
  );
}

function IssueModal({ orderId, onClose, onDone }: { orderId: string; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [category, setCategory] = useState("quality");
  const [description, setDescription] = useState("");
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (description.trim().length < 10) return setErr({ description: "Please describe the problem in at least 10 characters." });
    setBusy(true);
    try { await api.post(`/orders/${orderId}/issues`, { category, description: description.trim() }); toast.success("Issue reported. We'll look into it."); onDone(); onClose(); }
    catch (x) { setErr(x instanceof ApiError && x.details.length ? x.fieldErrors : { description: errorMessage(x) }); }
    finally { setBusy(false); }
  }
  return (
    <Modal title="Report a problem" onClose={onClose}>
      <form className="stack" onSubmit={submit} noValidate>
        <SelectField label="What kind of problem?" value={category} onChange={(e) => setCategory(e.target.value)} error={err.category}>
          <option value="quality">Quality of produce</option><option value="delivery">Delivery problem</option><option value="payment">Payment problem</option><option value="other">Other</option>
        </SelectField>
        <TextAreaField label="What happened?" value={description} onChange={(e) => setDescription(e.target.value)} error={err.description} maxLength={2000} hint="Share what you expected and what you received." />
        <div className="modal-foot"><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>{busy ? "Sending…" : "Send report"}</button></div>
      </form>
    </Modal>
  );
}

function ReviewModal({ orderId, onClose, onDone }: { orderId: string; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await api.post(`/orders/${orderId}/reviews`, { rating, comment: comment.trim() }); toast.success("Thanks for your review!"); onDone(); onClose(); }
    catch (x) { setError(errorMessage(x)); }
    finally { setBusy(false); }
  }
  return (
    <Modal title="Rate this farmer" onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <StarPicker value={rating} onChange={setRating} />
        <TextAreaField label="Tell others about it (optional)" value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} />
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="modal-foot"><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>{busy ? "Sending…" : "Submit review"}</button></div>
      </form>
    </Modal>
  );
}

function CancelModal({ orderId, onClose, onDone }: { orderId: string; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  async function go() {
    setBusy(true);
    try { await api.post(`/orders/${orderId}/cancel`, { reason: reason.trim() }); toast.info("Order cancelled. The stock was released."); onDone(); onClose(); }
    catch (e) { toast.error(errorMessage(e)); onDone(); onClose(); }
    finally { setBusy(false); }
  }
  return (
    <Modal title="Cancel this order?" onClose={onClose} footer={<><button className="btn btn-ghost" onClick={onClose}>Keep order</button><button className="btn btn-danger" onClick={go} disabled={busy}>{busy ? "Cancelling…" : "Cancel order"}</button></>}>
      <p>The reserved stock goes back to the farmer. This can't be undone.</p>
      <TextAreaField label="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} />
    </Modal>
  );
}

export default function OrderDetail() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const order = useAsync((s) => api.get<Order>(`/orders/${id}`, undefined, s).then((r) => r.data), [id]);
  const history = useAsync((s) => api.get<OrderHistoryItem[]>(`/orders/${id}/history`, undefined, s).then((r) => r.data), [id]);
  const delivery = useAsync((s) => api.get<Delivery>(`/orders/${id}/delivery`, undefined, s).then((r) => r.data).catch(() => null), [id]);
  const issues = useAsync((s) => api.get<Issue[]>(`/orders/${id}/issues`, undefined, s).then((r) => r.data).catch(() => [] as Issue[]), [id]);
  const farmer = useAsync((s) => (order.data ? api.get<PublicFarmer>(`/farmers/${order.data.farmer_id}`, undefined, s).then((r) => r.data).catch(() => null) : Promise.resolve(null)), [order.data?.farmer_id]);
  const [modal, setModal] = useState<null | "cancel" | "issue" | "review">(null);
  const status = order.data?.status;

  const refresh = () => { order.reload(); history.reload(); delivery.reload(); issues.reload(); };
  useEffect(() => {
    if (status !== "pending_payment" && status !== "paid") return;
    const t = window.setInterval(refresh, 30000);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  if (order.loading && !order.data) return <div className="wrap page stack"><Skeleton style={{ height: 40, width: "50%" }} /><Skeleton style={{ height: 200 }} /></div>;
  if (order.error) return <div className="wrap">{order.error.toLowerCase().includes("not found") ? <EmptyState icon="🧾" title="Order not found" action={{ to: "/orders", label: "My orders" }}>It may belong to another account.</EmptyState> : <ErrorState message={order.error} onRetry={order.reload} />}</div>;
  const o = order.data!;
  const isBuyer = user?.id === o.buyer_id;
  const canCancel = o.status === "pending_payment" && (isBuyer || user?.id === o.farmer_id);
  const canReport = (o.status === "paid" || o.status === "completed") && !!user && user.role !== "admin";

  return (
    <div className="wrap page">
      <nav className="crumbs"><Link to={user?.role === "farmer" ? "/farm/orders" : "/orders"}>Orders</Link> › <span>#{shortId(o.id)}</span></nav>
      <div className="page-head">
        <div><h1>Order #{shortId(o.id)}</h1><p className="muted">Placed {dateTime(o.created_at)}{farmer.data ? ` · ${isBuyer ? "From" : "Farm"}: ${farmer.data.farm_name || farmer.data.full_name}` : ""}</p></div>
        <span className={`badge ${ORDER_STATUS_BADGE[o.status]}`} style={{ fontSize: 14, padding: "5px 14px" }}>{ORDER_STATUS_LABEL[o.status]}</span>
      </div>
      <Timeline order={o} delivery={delivery.data} />

      <div className="order-grid">
        <div className="stack">
          {isBuyer && o.status === "pending_payment" && <PayPanel order={o} onChanged={refresh} />}
          {o.status === "expired" && <div className="alert alert-warn">This order expired because it wasn't paid in time. The stock was released. <Link to="/browse">Browse again</Link></div>}
          <section className="card card-pad stack" aria-label="Items">
            <h3>Items</h3>
            {o.lines.map((l) => (
              <div key={l.listing_id} className="row"><div><Link to={`/listings/${l.listing_id}`}><b>{l.produce_name}</b></Link><div className="muted small">{qty(l.quantity)} {l.quantity_unit} × {kes(l.unit_price)}</div></div><b>{kes(l.line_total)}</b></div>
            ))}
            <div className="row total"><span>Total</span><b className="price">{kes(o.total_amount)}</b></div>
          </section>
          {issues.data && issues.data.length > 0 && (
            <section className="card card-pad stack" aria-label="Issues">
              <h3>Reported problems</h3>
              {issues.data.map((i) => (
                <div key={i.id} className="alert alert-warn"><div className="row"><b>{i.category}</b><span className="badge b-off">{i.status}</span></div><p>{i.description}</p>{i.resolution && <p><b>Resolution:</b> {i.resolution}</p>}</div>
              ))}
            </section>
          )}
        </div>
        <div className="stack">
          <section className="card card-pad stack" aria-label="Delivery">
            <h3>{o.delivery_method === "delivery" ? "🚚 Delivery" : "🚜 Collection"}</h3>
            {o.delivery_location && <p>{o.delivery_location}</p>}
            {delivery.data ? (
              <>
                <span className="badge b-ok" style={{ justifySelf: "start" }}>{delivery.data.status}</span>
                {delivery.data.events.map((e, i) => <p key={i} className="small muted">{dateTime(e.created_at)}: {e.note || e.to_status}</p>)}
              </>
            ) : <p className="muted small">{o.status === "paid" ? "The farmer is preparing your order. Updates will appear here." : "Delivery updates start after payment."}</p>}
          </section>
          <section className="card card-pad stack" aria-label="History">
            <h3>History</h3>
            {(history.data ?? []).map((h, i) => <p key={i} className="small"><span className="muted">{dateTime(h.created_at)}</span> · {ORDER_STATUS_LABEL[h.to_status] ?? h.to_status}{h.note ? ` (${h.note})` : ""}</p>)}
          </section>
          <div className="stack">
            {isBuyer && o.status === "completed" && <button className="btn btn-accent btn-block" onClick={() => setModal("review")}>⭐ Rate this farmer</button>}
            {canReport && <button className="btn btn-ghost btn-block" onClick={() => setModal("issue")}>Report a problem</button>}
            {canCancel && <button className="btn btn-danger btn-block" onClick={() => setModal("cancel")}>Cancel order</button>}
          </div>
        </div>
      </div>
      {modal === "cancel" && <CancelModal orderId={o.id} onClose={() => setModal(null)} onDone={refresh} />}
      {modal === "issue" && <IssueModal orderId={o.id} onClose={() => setModal(null)} onDone={refresh} />}
      {modal === "review" && <ReviewModal orderId={o.id} onClose={() => setModal(null)} onDone={refresh} />}
    </div>
  );
}
