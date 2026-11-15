import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Delivery, Order } from "../../api/types";
import { json, listing, mockApi, ok, renderApp } from "../../test/helpers";
import { RequireAuth } from "../../auth/RequireAuth";
import { DeliveryPanel } from "./DeliveryPanel";
import Issues from "./Issues";
import Listings from "./Listings";
import Overview from "./Overview";
import Users from "./Users";

afterEach(() => vi.unstubAllGlobals());
const page = { pagination: { page: 1, page_size: 15, total_items: 1, total_pages: 1 } };
const user = { id: "u9", full_name: "Mary Farmer", email: "mary@example.test", phone: null, role: "farmer", is_active: true, date_joined: "2026-01-01T00:00:00Z" };

describe("admin access", () => {
  it("keeps non-admins out of admin pages", async () => {
    mockApi([]);
    renderApp(<Routes><Route path="/admin" element={<RequireAuth roles={["admin"]}><Overview /></RequireAuth>} /><Route path="/forbidden" element={<p>Not allowed here</p>} /></Routes>, "/admin");
    expect(await screen.findByText("Not allowed here")).toBeInTheDocument();
  });
});

describe("overview", () => {
  it("shows platform numbers from the summary report", async () => {
    mockApi([(u) => (u.pathname.endsWith("/admin/reports/summary") ? ok({
      users: { total: 4, by_role: { farmer: 1, buyer: 2, admin: 1 }, suspended: 1 }, listings: { total: 3, active_visible: 2, inactive: 0, hidden_by_admin: 1 },
      orders: { total: 5, by_status: { paid: 2, pending_payment: 1 }, paid_value_ksh: "1500.00" }, payments: { by_status: { succeeded: 2 } }, deliveries: { by_status: {} },
      issues: { total: 2, by_status: { open: 1, investigating: 1 } }, reviews: { total: 6, hidden: 1 }, inspections: { total: 3, published: 2 }, demand_requests: { by_status: {} },
    }) : undefined)]);
    renderApp(<Overview />);
    expect(await screen.findByText("Platform overview")).toBeInTheDocument();
    expect(await screen.findByText(/1 farmers · 2 buyers · 1 suspended/)).toBeInTheDocument();
    expect(screen.getByText(/Paid value/)).toBeInTheDocument();
  });
});

describe("users", () => {
  it("requires a reason to suspend and sends it to the API", async () => {
    const api = mockApi([
      (u) => (u.pathname.endsWith("/admin/users") ? ok([user], page) : undefined),
      (u, init) => (u.pathname.endsWith("/admin/users/u9/status") && init.method === "PATCH" ? ok({ ...user, is_active: false }) : undefined),
    ]);
    renderApp(<Users />);
    await userEvent.click(await screen.findByRole("button", { name: "Suspend" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Suspend account" }));
    expect(await within(dialog).findByText("Reason is required.")).toBeInTheDocument();
    expect(api.find("/admin/users/u9/status", "PATCH")).toHaveLength(0);
    await userEvent.type(within(dialog).getByLabelText("Reason"), "Fake produce");
    await userEvent.click(within(dialog).getByRole("button", { name: "Suspend account" }));
    await waitFor(() => expect(api.find("/admin/users/u9/status", "PATCH")).toHaveLength(1));
    expect(JSON.parse(api.find("/admin/users/u9/status", "PATCH")[0].init.body as string)).toEqual({ is_active: false, reason: "Fake produce" });
  });
});

describe("listings moderation", () => {
  it("hides a listing with a reason and keeps farmer-declared wording", async () => {
    const api = mockApi([
      (u) => (u.pathname.endsWith("/admin/listings") ? ok([listing()], page) : undefined),
      (u, init) => (u.pathname.endsWith("/admin/listings/l1/moderation") && init.method === "PATCH" ? ok(listing({ moderation_hidden: true })) : undefined),
    ]);
    renderApp(<Listings />);
    expect(await screen.findByText(/Farmer-declared: Farmer-declared Grade A/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Hide" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Reason"), "Misleading photo");
    await userEvent.click(within(dialog).getByRole("button", { name: "Hide listing" }));
    await waitFor(() => expect(api.find("/admin/listings/l1/moderation", "PATCH")).toHaveLength(1));
    expect(JSON.parse(api.find("/admin/listings/l1/moderation", "PATCH")[0].init.body as string)).toEqual({ hidden: true, reason: "Misleading photo" });
  });

  it("records an inspection as independent, separate from the farmer's grade", async () => {
    const api = mockApi([
      (u) => (u.pathname.endsWith("/admin/listings") ? ok([listing()], page) : undefined),
      (u, init) => (u.pathname.endsWith("/listings/l1/inspections") ? (init.method === "POST" ? json(201, { data: { id: "i1" } }) : ok([], page)) : undefined),
    ]);
    renderApp(<Listings />);
    await userEvent.click(await screen.findByRole("button", { name: "Inspections" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/independently inspected/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Record inspection" }));
    expect(await within(dialog).findByText(/Say what was inspected/)).toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText("What was inspected"), "Lot 14");
    await userEvent.click(within(dialog).getByRole("button", { name: "Record inspection" }));
    await waitFor(() => expect(api.find("/listings/l1/inspections", "POST")).toHaveLength(1));
    expect(JSON.parse(api.find("/listings/l1/inspections", "POST")[0].init.body as string)).toMatchObject({ scope: "Lot 14", result: "passed", is_published: true });
  });
});

describe("issues", () => {
  it("needs an outcome note to resolve an issue", async () => {
    const issue = { id: "s1", order_id: "o1aaaaaaaa", category: "quality", description: "Tomatoes were bruised", status: "open", resolution: "", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
    const api = mockApi([
      (u) => (u.pathname.endsWith("/admin/issues") ? ok([issue], page) : undefined),
      (u, init) => (u.pathname.endsWith("/admin/issues/s1") && init.method === "PATCH" ? ok({ ...issue, status: "resolved" }) : undefined),
    ]);
    renderApp(<Issues />);
    await userEvent.click(await screen.findByRole("button", { name: "Update" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.selectOptions(within(dialog).getByLabelText("Status"), "resolved");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByText(/Add a note for the buyer/)).toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText("Note to the buyer"), "Partial refund agreed");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.find("/admin/issues/s1", "PATCH")).toHaveLength(1));
    expect(JSON.parse(api.find("/admin/issues/s1", "PATCH")[0].init.body as string)).toEqual({ status: "resolved", resolution: "Partial refund agreed" });
  });
});

describe("delivery operations", () => {
  const order = { id: "o1", status: "paid" } as Order;
  const delivery = (status: Delivery["status"]): Delivery => ({ id: "d1", order_id: "o1", method: "delivery", location: "Nairobi", status, events: [], created_at: "", updated_at: "" });
  it("creates the delivery record for a paid order", async () => {
    const api = mockApi([(u, init) => (u.pathname.endsWith("/orders/o1/delivery") && init.method === "POST" ? json(201, { data: delivery("pending") }) : undefined)]);
    const changed = vi.fn();
    renderApp(<DeliveryPanel order={order} delivery={null} onChanged={changed} />);
    await userEvent.click(await screen.findByRole("button", { name: "Create delivery record" }));
    await waitFor(() => expect(changed).toHaveBeenCalled());
    expect(api.find("/orders/o1/delivery", "POST")).toHaveLength(1);
  });
  it("only offers legal next states and sends the note", async () => {
    const api = mockApi([(u, init) => (u.pathname.endsWith("/deliveries/d1") && init.method === "PATCH" ? ok(delivery("dispatched")) : undefined)]);
    renderApp(<DeliveryPanel order={order} delivery={delivery("pending")} onChanged={() => {}} />);
    const select = await screen.findByLabelText("Move to");
    expect([...select.querySelectorAll("option")].map((o) => o.getAttribute("value"))).toEqual(["dispatched", "failed"]);
    await userEvent.type(screen.getByLabelText("Note (optional)"), "Left depot");
    await userEvent.click(screen.getByRole("button", { name: "Update delivery" }));
    await waitFor(() => expect(api.find("/deliveries/d1", "PATCH")).toHaveLength(1));
    expect(JSON.parse(api.find("/deliveries/d1", "PATCH")[0].init.body as string)).toEqual({ status: "dispatched", note: "Left depot" });
  });
});
