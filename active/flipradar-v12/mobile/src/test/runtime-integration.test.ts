import { readCapabilities } from "@/features/runtime/capabilities";
import { dealSummary } from "@/features/workspace/dealSummary";
import type { FinancialDeal } from "@/api/mappers/deal";
import { fetchRadarPage } from "@/api/endpoints/radar";
import { apiRequest } from "@/api/client";

jest.mock("@/api/client", () => ({
  apiRequest: jest.fn().mockResolvedValue({ items: [], next_before_id: null }),
}));
jest.mock("@/utils/config", () => ({ radarSource: () => "universal" }));

describe("Server capabilities", () => {
  it("preserves existing APIs that do not advertise capabilities", () => {
    expect(readCapabilities(undefined).watchlist).toBe(true);
    expect(readCapabilities(undefined).deals_read).toBe(true);
  });
  it("does not enable unsupported V12 operations", () => {
    const capabilities = readCapabilities(undefined, true);
    expect(capabilities.search_platforms).toEqual(["OLX"]);
    expect(capabilities.search_purposes).toEqual(["cheap"]);
    expect(capabilities.watchlist).toBe(false);
    expect(capabilities.deals).toBe(false);
    expect(capabilities.deals_read).toBe(false);
  });
  it("recognizes readonly mode and treats non-boolean feature values as unavailable", () => {
    const capabilities = readCapabilities(
      {
        read_only: true,
        watchlist: "yes",
        deals_read: true,
        search_platforms: ["OLX", null, 10],
        radar_scope: "global",
      },
      true,
    );
    expect(capabilities.read_only).toBe(true);
    expect(capabilities.watchlist).toBe(false);
    expect(capabilities.deals_read).toBe(true);
    expect(capabilities.search_platforms).toEqual(["OLX"]);
    expect(capabilities.radar_scope).toBe("global");
    expect(capabilities.plan_requests).toBe(false);
  });
});

const deal: FinancialDeal = {
  id: "legacy-1",
  status: "LISTED",
  purchase_minor: 90000,
  cost_minor: 16000,
  sale_minor: null,
  realized_profit_minor: null,
  financials_complete: true,
};

describe("Existing inventory data", () => {
  it("sums actual purchase prices and costs", () => {
    expect(dealSummary([deal])).toMatchObject({
      capital: 106000,
      inventory: 90000,
      costs: 16000,
      open: 1,
      sold: 0,
    });
  });
  it("does not present missing purchase records as zero capital", () => {
    expect(
      dealSummary([{ ...deal, purchase_minor: 0, financials_complete: false }]),
    ).toMatchObject({
      capital: null,
      inventory: null,
      costs: null,
      incomplete: 1,
    });
  });
  it("keeps a realized loss and marks unknown sale profit as unknown", () => {
    expect(
      dealSummary([{ ...deal, status: "SOLD", realized_profit_minor: -5000 }])
        .profit,
    ).toBe(-5000);
    expect(
      dealSummary([{ ...deal, status: "SOLD", realized_profit_minor: null }])
        .profit,
    ).toBeNull();
  });
  it("includes preparation and pickup in active inventory", () => {
    expect(
      dealSummary([
        { ...deal, status: "PICKUP" },
        { ...deal, status: "PREPARING" },
      ]).open,
    ).toBe(2);
  });
});

describe("Radar contract", () => {
  it("sends filter scope before server pagination without changing the endpoint", async () => {
    await fetchRadarPage({
      limit: 30,
      beforeId: 123,
      q: " RTX 4070 ",
      minPriceMinor: 0,
      maxPriceMinor: 150000,
      minProfitMinor: 40000,
      minRoiBps: 2000,
      category: "ELECTRONICS",
      platforms: ["OLX", "FACEBOOK"],
    });
    const path = (apiRequest as jest.Mock).mock.calls.at(-1)[0] as string;
    const url = new URL(path, "https://unit.test");
    expect(url.pathname).toBe("/api/v1/universal/mobile-radar");
    expect(Object.fromEntries(url.searchParams)).toMatchObject({
      before_id: "123",
      q: "RTX 4070",
      min_price_minor: "0",
      max_price_minor: "150000",
      min_profit_minor: "40000",
      min_roi_bps: "2000",
      category: "ELECTRONICS",
      platform: "OLX,FACEBOOK",
    });
  });
  it("retains the plain query contract when additional filters are omitted", async () => {
    await fetchRadarPage({ q: "x".repeat(200) });
    const path = (apiRequest as jest.Mock).mock.calls.at(-1)[0] as string;
    const url = new URL(path, "https://unit.test");
    expect(url.searchParams.get("q")).toHaveLength(120);
    expect(url.searchParams.has("max_price_minor")).toBe(false);
    expect(url.searchParams.has("platform")).toBe(false);
  });
});
