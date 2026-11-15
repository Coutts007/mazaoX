/**
 * Shopping cart kept in the browser (localStorage, best effort). Prices shown here are for display only:
 * the server recalculates every price and total when the order is placed.
 * Orders are one farmer per order, so a cart holds items from a single farmer.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Listing } from "../api/types";

export interface CartItem {
  listingId: string;
  farmerId: string;
  name: string;
  slug: string;
  unit: string;
  price: string; // display only
  quantity: number;
  max: number | null; // last known availability
  place: string;
  image: string | null;
}

interface CartState {
  items: CartItem[];
  count: number;
  total: number;
  farmerId: string | null;
  /** returns "conflict" when the cart holds another farmer's produce */
  add: (listing: Listing, quantity: number) => "added" | "conflict";
  replaceWith: (listing: Listing, quantity: number) => void;
  setQuantity: (listingId: string, quantity: number) => void;
  remove: (listingId: string) => void;
  clear: () => void;
  /** refresh the last known availability of an item (and trim the quantity if it no longer fits) */
  syncMax: (listingId: string, max: number | null) => void;
}

const KEY = "mazaox.cart.v1";
const CartContext = createContext<CartState | null>(null);

function load(): CartItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function toItem(l: Listing, quantity: number): CartItem {
  return {
    listingId: l.id,
    farmerId: l.farmer_id,
    name: l.produce_name,
    slug: l.category.slug,
    unit: l.quantity_unit,
    price: l.price_per_unit,
    quantity,
    max: l.availability ? Number(l.availability.available) : null,
    place: [l.locality, l.county].filter(Boolean).join(", "),
    image: l.images[0]?.url ?? null,
  };
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(load);
  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(items));
    } catch {
      /* storage unavailable: the cart still works for this visit */
    }
  }, [items]);

  const clampQ = (q: number, max: number | null) => Math.max(1, max !== null ? Math.min(q, Math.floor(max)) : q);

  // The conflict decision must be made synchronously (the caller shows a dialog), so read the latest items from a ref.
  const itemsRef = useRef(items);
  itemsRef.current = items;
  const commit = useCallback((next: CartItem[]) => {
    itemsRef.current = next;
    setItems(next);
  }, []);

  const add = useCallback(
    (listing: Listing, quantity: number) => {
      const cur = itemsRef.current;
      if (cur.length && cur[0].farmerId !== listing.farmer_id) return "conflict" as const;
      const existing = cur.find((i) => i.listingId === listing.id);
      const fresh = toItem(listing, quantity);
      commit(existing ? cur.map((i) => (i.listingId === listing.id ? { ...fresh, quantity: clampQ(i.quantity + quantity, fresh.max) } : i)) : [...cur, { ...fresh, quantity: clampQ(quantity, fresh.max) }]);
      return "added" as const;
    },
    [commit],
  );
  const replaceWith = useCallback((listing: Listing, quantity: number) => commit([toItem(listing, quantity)]), [commit]);
  const setQuantity = useCallback((id: string, q: number) => setItems((cur) => cur.map((i) => (i.listingId === id ? { ...i, quantity: clampQ(q, i.max) } : i))), []);
  const remove = useCallback((id: string) => setItems((cur) => cur.filter((i) => i.listingId !== id)), []);
  const clear = useCallback(() => setItems([]), []);
  const syncMax = useCallback(
    (id: string, max: number | null) => setItems((cur) => cur.map((i) => (i.listingId === id ? { ...i, max, quantity: max !== null && max >= 1 ? Math.min(i.quantity, Math.floor(max)) : i.quantity } : i))),
    [],
  );

  const value = useMemo<CartState>(
    () => ({
      items,
      count: items.length,
      total: items.reduce((n, i) => n + Number(i.price) * i.quantity, 0),
      farmerId: items[0]?.farmerId ?? null,
      add,
      replaceWith,
      setQuantity,
      remove,
      clear,
      syncMax,
    }),
    [items, add, replaceWith, setQuantity, remove, clear, syncMax],
  );
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartState {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used inside <CartProvider>");
  return ctx;
}
