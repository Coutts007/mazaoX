import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { listing } from "../test/helpers";
import { CartProvider, useCart } from "./CartContext";

const wrapper = ({ children }: { children: ReactNode }) => <CartProvider>{children}</CartProvider>;

describe("cart", () => {
  beforeEach(() => localStorage.clear());

  it("merges the same listing and never exceeds known availability", () => {
    const { result } = renderHook(() => useCart(), { wrapper });
    act(() => { result.current.add(listing({ availability: { available: "5.000", in_stock: true } }), 3); });
    act(() => { result.current.add(listing({ availability: { available: "5.000", in_stock: true } }), 4); });
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].quantity).toBe(5);
  });

  it("refuses a second farmer's produce (orders are one farmer at a time) until the cart is replaced", () => {
    const { result } = renderHook(() => useCart(), { wrapper });
    act(() => { result.current.add(listing(), 1); });
    let outcome = "";
    act(() => { outcome = result.current.add(listing({ id: "l2", farmer_id: "f2" }), 1); });
    expect(outcome).toBe("conflict");
    expect(result.current.items.map((i) => i.listingId)).toEqual(["l1"]);
    act(() => result.current.replaceWith(listing({ id: "l2", farmer_id: "f2" }), 2));
    expect(result.current.items.map((i) => i.listingId)).toEqual(["l2"]);
  });

  it("persists in localStorage and trims quantity when stock drops", () => {
    const first = renderHook(() => useCart(), { wrapper });
    act(() => { first.result.current.add(listing(), 10); });
    first.unmount();
    const second = renderHook(() => useCart(), { wrapper });
    expect(second.result.current.items[0].quantity).toBe(10);
    act(() => second.result.current.syncMax("l1", 4));
    expect(second.result.current.items[0].quantity).toBe(4);
    expect(second.result.current.total).toBe(85 * 4);
  });

  it("survives unreadable storage", () => {
    localStorage.setItem("mazaox.cart.v1", "{not json");
    const { result } = renderHook(() => useCart(), { wrapper });
    expect(result.current.items).toEqual([]);
  });
});
