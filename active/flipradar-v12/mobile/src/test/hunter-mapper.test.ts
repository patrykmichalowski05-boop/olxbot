import { mapRadarItem, mapSnapshotDetail } from "@/api/mappers/opportunity";
import { opportunityInsight } from "@/features/opportunity/presentation";
import type { RadarApiItem } from "@/api/types/radar";

const item: RadarApiItem = {
  snapshot_id: 123,
  title: "RTX 4070 12GB",
  platform: "OLX",
  decision: "WATCH",
  price_minor: 100000,
  observed_at: "2026-10-15T12:00:00Z",
  url: "https://www.olx.pl/d/oferta/example-ID1.html",
  valuation: {
    quick_sale: 1500,
    profit: 300,
    total_cost: 200,
    max_buy: 1100,
    roi_bps: 2500,
    summary: "Porównano pięć ofert.",
    issues: ["Ceny ofertowe"],
    confidence: "LOW",
  },
};

it("preserves ROI on total invested capital, currency units and costs", () => {
  const card = mapRadarItem(item);
  expect(card.roiBps).toBe(2500);
  expect(card.operatingProfitMinor).toBe(30000);
  expect(mapSnapshotDetail(item).baseScenario?.costsMinor).toBe(20000);
  expect(mapSnapshotDetail(item).maxBuyMinor).toBe(110000);
});

it("uses legacy bridge amounts and category consistently with server-side filters", () => {
  const card = mapRadarItem({
    ...item,
    title: "Sprzęt z magazynu",
    profit_minor: 4567,
    roi_bps: 1789,
    category: "ELECTRONICS",
    valuation: { quick_sale: 1500, total_cost: 1454.33 },
  });
  expect(card.operatingProfitMinor).toBe(4567);
  expect(card.roiBps).toBe(1789);
  expect(card.category).toBe("ELECTRONICS");
});

it("labels deterministic comparables without claiming AI output", () => {
  expect(opportunityInsight(mapRadarItem(item))).toEqual({
    label: "Analiza rynku",
    text: "Porównano pięć ofert.",
  });
  expect(mapSnapshotDetail(item).risks).toEqual(["Ceny ofertowe"]);
});

it("retains legacy AI fields and never treats missing valuation as zero profit", () => {
  expect(
    mapRadarItem({
      ...item,
      valuation: { ai_summary: "Ocena AI", ai_issues: ["Stan"] },
    }).insightSource,
  ).toBe("ai");
  const missing = mapRadarItem({
    ...item,
    decision: "NO_RELIABLE_VALUATION",
    valuation: { quick_sale: null, profit: null },
  });
  expect(missing.hasValuation).toBe(false);
  expect(missing.operatingProfitMinor).toBeNull();
});
