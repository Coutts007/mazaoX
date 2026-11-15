import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Order } from "../api/types";
import { buyer, json, listing, mockApi, ok, renderApp } from "../test/helpers";
import Browse from "./Browse";
import Cart from "./Cart";
import ListingDetail from "./ListingDetail";
import OrderDetail from "./OrderDetail";
import { Route, Routes } from "react-router-dom";

const order = (over: Partial<Order> = {}): Order => ({
  id: "o1234567-aaaa", buyer_id: buyer.id, farmer_id: "f1", status: "pending_payment", delivery_method: "collection", delivery_location: "", total_amount: "170.00", currency: "KSh",
  lines: [{ listing_id: "l1", produce_name: "Roma Tomatoes", unit_price: "85.00", quantity: "2.000", quantity_unit: "kg", line_total: "170.00" }],
  payment_due_by: new Date(Date.now() + 10 * 60000).toISOString(), created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", ...over,
});

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("browse", () => {
  it("searches after a pause, keeps filters in the URL and lets you remove a chip", async () => {
    const api = mockApi([
      (u) => (u.pathname.endsWith("/categories") ? ok([{ id: "c1", name: "Tomatoes", slug: "tomatoes" }]) : undefined),
      (u) => (u.pathname.endsWith("/listings") ? ok([listing()], { pagination: { page: 1, page_size: 12, total_items: 1, total_pages: 1 } }) : undefined),
    ]);
    renderApp(<Browse />, "/browse");
    expect(await screen.findByText("Roma Tomatoes")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("searchbox", { name: "Search produce" }), "kale");
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/browse?q=kale"), { timeout: 2000 });
    await waitFor(() => expect(api.find("/listings").some((c) => c.url.searchParams.get("q") === "kale")).toBe(true));
    await userEvent.click(screen.getByRole("button", { name: "Remove filter “kale”" }));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/browse$/), { timeout: 2000 });
  });

  it("shows a friendly empty state", async () => {
    mockApi([(u) => (u.pathname.endsWith("/categories") ? ok([]) : u.pathname.endsWith("/listings") ? ok([], { pagination: { page: 1, page_size: 12, total_items: 0, total_pages: 1 } }) : undefined)]);
    renderApp(<Browse />, "/browse?q=zzz");
    expect(await screen.findByText("Nothing matches yet")).toBeInTheDocument();
  });
});

describe("listing detail", () => {
  it("labels the grade as farmer-declared, never verified", async () => {
    mockApi([
      (u) => (u.pathname.endsWith("/listings/l1") ? ok(listing()) : undefined),
      (u) => (u.pathname.endsWith("/inspections") ? ok([], { pagination: { page: 1, page_size: 20, total_items: 0, total_pages: 1 } }) : undefined),
      (u) => (u.pathname.includes("/farmers/") ? ok({ id: "f1", full_name: "Mwangi Demo", farm_name: "", county: "", locality: "", bio: "", member_since: "2026-01-01T00:00:00Z" }, { summary: { average_rating: null, review_count: 0, distribution: {} } }) : undefined),
    ]);
    renderApp(<Routes><Route path="/listings/:id" element={<ListingDetail />} /></Routes>, "/listings/l1");
    expect(await screen.findByRole("heading", { name: /Roma Tomatoes/ })).toBeInTheDocument();
    expect(screen.getByText(/declared by the farmer/)).toBeInTheDocument();
    expect(screen.getByText(/No independent inspection has been recorded/)).toBeInTheDocument();
    expect(screen.queryByText(/Independently inspected on/)).not.toBeInTheDocument();
  });
});

describe("checkout", () => {
  async function fillCart() {
    localStorage.setItem("mazaox.cart.v1", JSON.stringify([{ listingId: "l1", farmerId: "f1", name: "Roma Tomatoes", slug: "tomatoes", unit: "kg", price: "85.00", quantity: 2, max: 50, place: "Meru", image: null }]));
  }
  const base = [
    (u: URL) => (u.pathname.includes("/availability") ? ok({ available: "50.000" }) : undefined),
    (u: URL) => (u.pathname.includes("/farmers/") ? ok({ id: "f1", full_name: "Mwangi Demo", farm_name: "", county: "", locality: "", bio: "", member_since: "2026-01-01T00:00:00Z" }) : undefined),
  ];

  it("sends no prices, reuses the same Idempotency-Key when retrying, and clears the cart on success", async () => {
    await fillCart();
    let attempts = 0;
    const api = mockApi([
      ...base,
      (u, init) => {
        if (u.pathname.endsWith("/orders") && init.method === "POST") {
          attempts++;
          return attempts === 1 ? json(503, { error: { code: "UNAVAILABLE", message: "Temporary problem." } }) : json(201, { data: order() });
        }
      },
    ]);
    renderApp(<Routes><Route path="/cart" element={<Cart />} /><Route path="/orders/:id" element={<p>ORDER PAGE</p>} /></Routes>, "/cart");
    const button = await screen.findByRole("button", { name: "Place order" });
    await userEvent.click(button);
    expect(await screen.findByText("Temporary problem.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Place order" }));
    expect(await screen.findByText("ORDER PAGE")).toBeInTheDocument();
    const posts = api.find("/orders", "POST");
    expect(posts).toHaveLength(2);
    const key = (c: { init: RequestInit }) => (c.init.headers as Record<string, string>)["Idempotency-Key"];
    expect(key(posts[0])).toBeTruthy();
    expect(key(posts[0])).toBe(key(posts[1]));
    const body = JSON.parse(String(posts[0].init.body));
    expect(body).toEqual({ items: [{ listing_id: "l1", quantity: "2", quantity_unit: "kg" }], delivery_method: "collection" });
    expect(JSON.stringify(body)).not.toMatch(/price|total/i);
    expect(localStorage.getItem("mazaox.cart.v1")).toBe("[]");
  });

  it("requires a delivery location for delivery orders and shows per-line stock errors", async () => {
    await fillCart();
    mockApi([
      ...base,
      (u, init) => (u.pathname.endsWith("/orders") && init.method === "POST"
        ? json(409, { error: { code: "INSUFFICIENT_STOCK", message: "Not enough stock.", details: [{ field: "items.0.quantity", message: "Only 1 kg left." }] } }) : undefined),
    ]);
    renderApp(<Cart />, "/cart");
    await userEvent.click(await screen.findByLabelText(/Deliver to me/));
    await userEvent.click(screen.getByRole("button", { name: "Place order" }));
    expect(await screen.findByText("Tell us where to deliver.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Delivery location"), "Kilimani");
    await userEvent.click(screen.getByRole("button", { name: "Place order" }));
    expect(await screen.findByText("Only 1 kg left.")).toBeInTheDocument();
  });
});

describe("order payment (simulated)", () => {
  it("never shows PIN or card fields, and re-reads the order from the server after paying", async () => {
    let status: Order["status"] = "pending_payment";
    const api = mockApi([
      (u) => (u.pathname.endsWith("/orders/o1234567-aaaa") ? ok(order({ status })) : undefined),
      (u) => (u.pathname.endsWith("/history") ? ok([]) : undefined),
      (u) => (u.pathname.endsWith("/delivery") ? json(404, { error: { code: "NOT_FOUND", message: "none" } }) : undefined),
      (u) => (u.pathname.endsWith("/issues") ? ok([]) : undefined),
      (u) => (u.pathname.includes("/farmers/") ? ok({ id: "f1", full_name: "Mwangi Demo", farm_name: "Mwangi Farm", county: "", locality: "", bio: "", member_since: "2026-01-01T00:00:00Z" }) : undefined),
      (u, init) => (u.pathname.endsWith("/payment-simulation") && init.method === "POST" ? json(201, { data: { id: "p1", order_id: "o1", amount: "170.00", currency: "KSh", status: "pending", failure_reason: "", mode: "simulated", created_at: "", completed_at: null } }) : undefined),
      (u, init) => {
        if (u.pathname.endsWith("/payments/simulations/p1/complete") && init.method === "POST") {
          status = "paid";
          return ok({ id: "p1", order_id: "o1", amount: "170.00", currency: "KSh", status: "succeeded", failure_reason: "", mode: "simulated", created_at: "", completed_at: "x" });
        }
      },
    ]);
    renderApp(<Routes><Route path="/orders/:id" element={<OrderDetail />} /></Routes>, "/orders/o1234567-aaaa");
    expect(await screen.findByText(/Demo payment\./)).toBeInTheDocument();
    expect(screen.queryByLabelText(/pin|cvv|card/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Pay with M-Pesa/ }));
    await userEvent.click(await screen.findByRole("button", { name: /Simulate successful payment/ }));
    const badge = await screen.findAllByText("Paid");
    expect(badge.length).toBeGreaterThan(0);
    expect(api.find("/orders/o1234567-aaaa").length).toBeGreaterThanOrEqual(2); // re-fetched after paying
    expect(screen.queryByRole("button", { name: /Pay with M-Pesa/ })).not.toBeInTheDocument();
  });
});
