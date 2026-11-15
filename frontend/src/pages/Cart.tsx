import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api, errorMessage, mediaUrl } from "../api/client";
import type { Order, PublicFarmer } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Quantity } from "../components/Bits";
import { EmptyState } from "../components/Feedback";
import { ProduceArt } from "../components/ProduceArt";
import { useToast } from "../components/Toasts";
import { useCart } from "../cart/CartContext";
import { kes } from "../lib/format";

function newKey() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `k-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function Cart() {
  const cart = useCart();
  const { user, ready } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [method, setMethod] = useState<"collection" | "delivery">("collection");
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lineErrors, setLineErrors] = useState<Record<number, string>>({});
  const [farmer, setFarmer] = useState<PublicFarmer | null>(null);
  const [locErr, setLocErr] = useState<string | null>(null);
  const keyRef = useRef<{ sig: string; key: string } | null>(null);

  // Refresh availability so buyers learn about stock changes before they submit.
  useEffect(() => {
    let off = false;
    cart.items.forEach((i) =>
      api.get<{ available: string }>(`/inventory/listings/${i.listingId}/availability`).then(
        (r) => !off && cart.syncMax(i.listingId, Number(r.data.available)),
        () => undefined,
      ),
    );
    return () => { off = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cart.items.map((i) => i.listingId).join(",")]);

  useEffect(() => {
    if (!cart.farmerId) { setFarmer(null); return; }
    api.get<PublicFarmer>(`/farmers/${cart.farmerId}`).then((r) => setFarmer(r.data), () => setFarmer(null));
  }, [cart.farmerId]);

  if (cart.items.length === 0) {
    return <div className="wrap page"><EmptyState icon="🛒" title="Your cart is empty" action={{ to: "/browse", label: "Browse fresh produce" }}>Add something from a farmer to get started.</EmptyState></div>;
  }

  const canOrder = !user || user.role === "buyer";

  async function place() {
    setError(null);
    setLineErrors({});
    setLocErr(null);
    if (!user) return navigate("/login", { state: { from: "/cart" } });
    if (method === "delivery" && !location.trim()) return setLocErr("Tell us where to deliver.");
    const items = cart.items.map((i) => ({ listing_id: i.listingId, quantity: String(i.quantity), quantity_unit: i.unit }));
    const sig = JSON.stringify({ items, method, location: location.trim() });
    // One Idempotency-Key per distinct checkout: a retry (double tap, flaky network) cannot create two orders.
    if (keyRef.current?.sig !== sig) keyRef.current = { sig, key: newKey() };
    setBusy(true);
    try {
      const res = await api.post<Order>("/orders", { items, delivery_method: method, ...(method === "delivery" ? { delivery_location: location.trim() } : {}) }, { idempotencyKey: keyRef.current.key });
      cart.clear();
      toast.success("Order placed! Complete the payment to confirm it.");
      navigate(`/orders/${res.data.id}`, { replace: true });
    } catch (e) {
      if (e instanceof ApiError) {
        const le: Record<number, string> = {};
        for (const d of e.details) {
          const m = /^items\.(\d+)\./.exec(d.field);
          if (m) le[Number(m[1])] = d.message;
        }
        setLineErrors(le);
        if (e.fieldErrors.delivery_location) setLocErr(e.fieldErrors.delivery_location);
        setError(Object.keys(le).length ? "Some items need your attention." : e.message);
        if (e.code === "INSUFFICIENT_STOCK") cart.items.forEach((i) => api.get<{ available: string }>(`/inventory/listings/${i.listingId}/availability`).then((r) => cart.syncMax(i.listingId, Number(r.data.available)), () => undefined));
      } else setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="wrap page">
      <div className="page-head"><h1>Your cart</h1><button className="btn btn-text" onClick={() => { cart.clear(); toast.info("Cart cleared"); }}>Clear cart</button></div>
      <div className="cart-grid">
        <section className="stack" aria-label="Items">
          {farmer && <p className="muted">From <b>{farmer.farm_name || farmer.full_name}</b>{farmer.county ? `, ${farmer.county}` : ""}. Orders are from one farmer at a time.</p>}
          {cart.items.map((i, idx) => (
            <div key={i.listingId} className="card card-pad cart-line">
              <Link to={`/listings/${i.listingId}`} className="cart-thumb">{i.image ? <img src={mediaUrl(i.image)} alt="" /> : <ProduceArt slug={i.slug} size={30} />}</Link>
              <div className="grow stack" style={{ gap: 6 }}>
                <div className="row"><Link to={`/listings/${i.listingId}`}><b>{i.name}</b></Link><button className="btn btn-text btn-sm" onClick={() => cart.remove(i.listingId)} aria-label={`Remove ${i.name}`}>Remove</button></div>
                <span className="muted small">{kes(i.price)} / {i.unit}{i.place ? ` · ${i.place}` : ""}</span>
                <div className="row">
                  <Quantity value={i.quantity} max={i.max} onChange={(n) => cart.setQuantity(i.listingId, n)} label={`Quantity of ${i.name}`} />
                  <b className="price">{kes(Number(i.price) * i.quantity)}</b>
                </div>
                {i.max !== null && i.max < 1 && <div className="alert alert-warn">This item just sold out. Remove it to continue.</div>}
                {i.max !== null && i.max >= 1 && i.quantity >= Math.floor(i.max) && <span className="muted small">Only {Math.floor(i.max)} {i.unit} available.</span>}
                {lineErrors[idx] && <div className="alert alert-error" role="alert">{lineErrors[idx]}</div>}
              </div>
            </div>
          ))}
        </section>
        <aside className="card card-pad stack summary" aria-label="Order summary">
          <h2>Checkout</h2>
          <fieldset className="radios">
            <legend>How do you want to get it?</legend>
            <label className={method === "collection" ? "on" : ""}><input type="radio" name="m" checked={method === "collection"} onChange={() => setMethod("collection")} /> Collect from the farm</label>
            <label className={method === "delivery" ? "on" : ""}><input type="radio" name="m" checked={method === "delivery"} onChange={() => setMethod("delivery")} /> Deliver to me</label>
          </fieldset>
          {method === "delivery" && (
            <div className="field">
              <label htmlFor="loc">Delivery location</label>
              <input id="loc" className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Estate, street or landmark" aria-invalid={!!locErr} autoComplete="street-address" />
              {locErr && <span className="err" role="alert">{locErr}</span>}
            </div>
          )}
          <div className="row"><span>Estimated total</span><b className="price">{kes(cart.total)}</b></div>
          <p className="muted small">The server recalculates prices and totals when you place the order. Stock is held for 15 minutes.</p>
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          {!canOrder ? <div className="alert alert-info">Only buyer accounts can place orders.</div> : (
            <button className="btn btn-primary btn-block" onClick={place} disabled={busy || !ready || cart.items.some((i) => i.max !== null && i.max < 1)}>
              {busy ? <span className="spinner" /> : null}{busy ? "Placing order…" : !ready ? "Checking your session…" : user ? "Place order" : "Log in to place order"}
            </button>
          )}
          <Link to="/browse" className="btn btn-text btn-block">Keep shopping</Link>
        </aside>
      </div>
    </div>
  );
}
