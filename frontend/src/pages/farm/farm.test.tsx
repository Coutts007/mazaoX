import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, listing, mockApi, ok, renderApp } from "../../test/helpers";
import ListingEditor, { checkImage } from "./ListingEditor";

afterEach(() => vi.unstubAllGlobals());

const cats = [{ id: "c1", name: "Tomatoes", slug: "tomatoes" }];
const file = (name: string, type: string, size = 1000) => new File([new Uint8Array(size)], name, { type });

describe("photo checks", () => {
  it("accepts JPEG/PNG/WebP under 5 MB and explains rejections", () => {
    expect(checkImage(file("a.jpg", "image/jpeg"))).toBeNull();
    expect(checkImage(file("a.webp", "image/webp"))).toBeNull();
    expect(checkImage(file("a.gif", "image/gif"))).toMatch(/JPEG, PNG or WebP/);
    expect(checkImage(file("big.png", "image/png", 5 * 1024 * 1024 + 1))).toMatch(/5 MB/);
  });
});

describe("listing editor", () => {
  it("validates before sending, then creates the listing with server-side pricing only and moves on to photos/stock", async () => {
    const api = mockApi([
      (u) => (u.pathname.endsWith("/categories") ? ok(cats) : undefined),
      (u, init) => (u.pathname.endsWith("/listings") && init.method === "POST" ? json(201, { data: listing({ id: "new1" }) }) : undefined),
      (u) => (u.pathname.endsWith("/listings/new1") ? ok(listing({ id: "new1" })) : undefined),
      (u) => (u.pathname.includes("/inventory/") ? ok({ listing_id: "new1", unit: "kg", on_hand: "0", reserved: "0", available: "0" }, { pagination: { page: 1, page_size: 8, total_items: 0, total_pages: 1 } }) : undefined),
    ]);
    renderApp(<Routes><Route path="/farm/listings/new" element={<ListingEditor />} /><Route path="/farm/listings/:id" element={<ListingEditor />} /></Routes>, "/farm/listings/new");
    await userEvent.click(await screen.findByRole("button", { name: "Create listing" }));
    expect(await screen.findByText("Choose a category.")).toBeInTheDocument();
    expect(screen.getByText("What are you selling?")).toBeInTheDocument();
    expect(api.find("/listings", "POST")).toHaveLength(0);

    await userEvent.selectOptions(screen.getByLabelText("Category"), "c1");
    await userEvent.type(screen.getByLabelText("Produce name"), "Roma tomatoes");
    await userEvent.type(screen.getByLabelText("Price per unit (KES)"), "85");
    await userEvent.selectOptions(screen.getByLabelText("County"), "Meru");
    await userEvent.click(screen.getByRole("button", { name: "Create listing" }));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/farm/listings/new1"));
    const body = JSON.parse(String(api.find("/listings", "POST")[0].init.body));
    expect(body).toMatchObject({ category_id: "c1", produce_name: "Roma tomatoes", price_per_unit: "85", county: "Meru", harvest_date: null });
    expect(await screen.findByRole("region", { name: "Photos" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Stock" })).toBeInTheDocument();
  });

  it("blocks bad photos in the browser and never uploads them", async () => {
    const api = mockApi([
      (u) => (u.pathname.endsWith("/categories") ? ok(cats) : undefined),
      (u) => (u.pathname.endsWith("/listings/l1") ? ok(listing()) : undefined),
      (u) => (u.pathname.includes("/inventory/") ? ok({ listing_id: "l1", unit: "kg", on_hand: "5", reserved: "0", available: "5" }, { pagination: { page: 1, page_size: 8, total_items: 0, total_pages: 1 } }) : undefined),
    ]);
    renderApp(<Routes><Route path="/farm/listings/:id" element={<ListingEditor />} /></Routes>, "/farm/listings/l1");
    const input = await screen.findByLabelText("Choose photos");
    await userEvent.upload(input, [file("notes.gif", "image/gif"), file("huge.png", "image/png", 6 * 1024 * 1024)], { applyAccept: false });
    expect(await screen.findByText(/notes\.gif: use a JPEG, PNG or WebP photo\./)).toBeInTheDocument();
    expect(screen.getByText(/huge\.png: photos must be 5 MB or smaller\./)).toBeInTheDocument();
    expect(api.find("/media", "POST")).toHaveLength(0);
  });

  it("asks for a reason when spoilage is recorded and sends the adjustment otherwise", async () => {
    const api = mockApi([
      (u) => (u.pathname.endsWith("/categories") ? ok(cats) : undefined),
      (u) => (u.pathname.endsWith("/listings/l1") ? ok(listing()) : undefined),
      (u, init) => (u.pathname.endsWith("/adjustments") && init.method === "POST" ? json(201, { data: {} }) : undefined),
      (u) => (u.pathname.includes("/inventory/") ? ok({ listing_id: "l1", unit: "kg", on_hand: "5", reserved: "0", available: "5" }, { pagination: { page: 1, page_size: 8, total_items: 0, total_pages: 1 } }) : undefined),
    ]);
    renderApp(<Routes><Route path="/farm/listings/:id" element={<ListingEditor />} /></Routes>, "/farm/listings/l1");
    await userEvent.selectOptions(await screen.findByLabelText("What happened?"), "spoilage");
    await userEvent.type(screen.getByLabelText("Quantity (kg)"), "2");
    await userEvent.click(screen.getByRole("button", { name: "Update stock" }));
    expect(await screen.findByText("A reason is required for this change.")).toBeInTheDocument();
    expect(api.find("/adjustments", "POST")).toHaveLength(0);
    await userEvent.type(screen.getByLabelText("Reason"), "Rain damage");
    await userEvent.click(screen.getByRole("button", { name: "Update stock" }));
    await waitFor(() => expect(api.find("/adjustments", "POST")).toHaveLength(1));
    expect(JSON.parse(String(api.find("/adjustments", "POST")[0].init.body))).toEqual({ movement_type: "spoilage", quantity: "2", reason: "Rain damage" });
  });
});
