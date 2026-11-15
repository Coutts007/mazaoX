import { useState } from "react";
import { api, errorMessage } from "../../api/client";
import type { Delivery, Order } from "../../api/types";
import { SelectField, TextField } from "../../components/Field";
import { useToast } from "../../components/Toasts";
import { dateTime } from "../../lib/format";
import { STATUS_BADGE } from "./shared";

const NEXT: Record<Delivery["status"], Delivery["status"][]> = { pending: ["dispatched", "failed"], dispatched: ["delivered", "failed"], failed: ["pending"], delivered: [] };
const LABEL: Record<string, string> = { pending: "Pending", dispatched: "Dispatched / ready for collection", delivered: "Delivered / collected", failed: "Failed" };

/** The administrator acts as delivery operator: creates the record once an order is paid, then moves it along. */
export function DeliveryPanel({ order, delivery, onChanged }: { order: Order; delivery: Delivery | null; onChanged: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [next, setNext] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | undefined>();
  const options = delivery ? NEXT[delivery.status] : [];
  const target = next || options[0] || "";
  async function run(fn: () => Promise<unknown>, done: string) {
    setBusy(true); setErr(undefined);
    try { await fn(); toast.success(done); setNote(""); setNext(""); onChanged(); } catch (x) { setErr(errorMessage(x)); } finally { setBusy(false); }
  }
  return (
    <section className="card card-pad stack" aria-label="Delivery operations">
      <h3>Delivery operations</h3>
      {!delivery ? (
        order.status === "paid"
          ? <><p className="small muted">This order is paid. Create the delivery record to start tracking fulfilment.</p><button className="btn btn-primary" disabled={busy} onClick={() => run(() => api.post(`/orders/${order.id}/delivery`), "Delivery record created")}>Create delivery record</button></>
          : <p className="small muted">A delivery record can be created once the order is paid.</p>
      ) : (
        <>
          <span className={`badge ${STATUS_BADGE[delivery.status]}`} style={{ justifySelf: "start" }}>{LABEL[delivery.status]}</span>
          {options.length > 0 ? (
            <>
              <SelectField label="Move to" value={target} onChange={(e) => setNext(e.target.value)}>{options.map((s) => <option key={s} value={s}>{LABEL[s]}</option>)}</SelectField>
              <TextField label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={255} error={err} />
              <button className="btn btn-primary" disabled={busy} onClick={() => run(() => api.patch(`/deliveries/${delivery.id}`, { status: target, note: note.trim() }), "Delivery updated")}>{busy ? "Saving…" : "Update delivery"}</button>
            </>
          ) : <p className="small muted">Delivered. Completing the delivery closes the order.</p>}
          {delivery.events.map((e, i) => <p key={i} className="small muted">{dateTime(e.created_at)}: {e.note || e.to_status}</p>)}
        </>
      )}
      {!delivery && err && <p className="err" role="alert">{err}</p>}
    </section>
  );
}
