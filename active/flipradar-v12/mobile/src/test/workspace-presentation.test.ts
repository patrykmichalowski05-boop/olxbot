import { mapRadarItem } from "@/api/mappers/opportunity";
import type { RadarApiItem } from "@/api/types/radar";
import {
  applyClientFilters,
  defaultFilters,
} from "@/features/radar/filterStore";
import {
  checkedRecently,
  confidenceLabel,
  loadedPriceSummary,
  offerTags,
  priceAssessment,
  priceAssessmentText,
  readMarket,
  safeOfferUrl,
  savedKeyFor,
  savedOfferId,
} from "@/features/workspace/presentation";
import { formatRelativeSync, formatUserDateTime } from "@/utils/datetime";

const raw: RadarApiItem = {
  snapshot_id: 25,
  title: "Komputer i5-12400F / RTX 3060 Ti / 32 GB RAM / 1 TB SSD",
  platform: "OLX",
  price_minor: 75000,
  observed_at: "2026-10-16T10:00:00Z",
  url: "https://www.olx.pl/d/oferta/test.html",
  decision: "WATCH",
  valuation: {
    quick_sale: 1900,
    profit: 800,
    roi_bps: 7500,
    market: {
      status: "OK",
      kind: "ASKING",
      sample_count: 28,
      median_minor: 299900,
      low_minor: 185000,
      high_minor: 439900,
      confidence: "LOW",
    },
  },
};
const card = mapRadarItem(raw);

describe("Price evidence without changing the backend decision", () => {
  it("preserves minor units and the existing server financial fields", () => {
    expect(card.market?.medianMinor).toBe(299900);
    expect(card.market?.sampleCount).toBe(28);
    expect(card.operatingProfitMinor).toBe(80000);
    expect(card.roiBps).toBe(7500);
    expect(card.decision).toBe("WATCH");
  });
  it("marks an unusually low asking price for verification", () => {
    expect(priceAssessment(card)).toEqual({
      label: "Podejrzanie tanio",
      tone: "warning",
      discountPercent: 75,
    });
    expect(priceAssessmentText(card)).toBe("o 75% poniżej typowej ceny");
    expect(card.decision).toBe("WATCH");
  });
  it.each([
    [230000, "Dobra cena"],
    [299900, "Cena typowa"],
    [350000, "Powyżej typowej ceny"],
  ])(
    "compares the price %s to its own variant median",
    (purchaseMinor, label) => {
      expect(priceAssessment({ ...card, purchaseMinor }).label).toBe(label);
    },
  );
  it("does not infer price quality from profit, a tiny sample or an invalid estimate", () => {
    expect(
      priceAssessment({ ...card, market: undefined }).discountPercent,
    ).toBeNull();
    expect(
      priceAssessment({ ...card, market: { ...card.market!, sampleCount: 2 } })
        .label,
    ).toBe("Brak oceny ceny");
    expect(
      priceAssessment({
        ...card,
        market: { ...card.market!, status: "NO_RELIABLE_VALUATION" },
      }).discountPercent,
    ).toBeNull();
    expect(
      priceAssessment({ ...card, purchaseMinor: null }).discountPercent,
    ).toBeNull();
  });
  it("ignores malformed or missing market fields", () => {
    expect(readMarket(null)).toBeUndefined();
    expect(readMarket([])).toBeUndefined();
    expect(
      readMarket({ median_minor: "299900", sample_count: NaN })?.medianMinor,
    ).toBeNull();
    expect(
      readMarket({ median_minor: -1, sample_count: -1 })?.sampleCount,
    ).toBeNull();
    expect(confidenceLabel("LOW")).toBe("ograniczona");
    expect(confidenceLabel("INTERNAL_MODEL_ERROR")).toBe("—");
  });
  it("summarizes only loaded asking prices without counting comparison samples twice", () => {
    const summary = loadedPriceSummary([
      card,
      { ...card, purchaseMinor: 100000 },
      { ...card, purchaseMinor: null },
    ]);
    expect(summary.count).toBe(3);
    expect(summary.pricedCount).toBe(2);
    expect(summary.medianMinor).toBe(87500);
    expect(summary.minMinor).toBe(75000);
    expect(summary.maxMinor).toBe(100000);
    expect(loadedPriceSummary([]).medianMinor).toBeNull();
  });
  it("extracts display tags only from the actual title", () => {
    expect(offerTags(card)).toEqual([
      "i5-12400F",
      "RTX 3060 Ti",
      "32 GB RAM",
      "1 TB SSD",
    ]);
    expect(offerTags({ ...card, title: "Przedmiot bez parametrów" })).toEqual(
      [],
    );
  });
  it("filters both price boundaries and excludes unknown prices", () => {
    const items = [
      card,
      { ...card, id: "b", purchaseMinor: 150000 },
      { ...card, id: "c", purchaseMinor: null },
    ];
    expect(
      applyClientFilters(items, {
        ...defaultFilters,
        minBudgetMinor: 100000,
        maxBudgetMinor: 160000,
      }).map((item) => item.id),
    ).toEqual(["b"]);
  });
});

describe("Offer links and saved records", () => {
  it("accepts supported HTTPS marketplace hosts", () => {
    expect(safeOfferUrl("OLX", raw.url)).toBe(raw.url);
    expect(
      safeOfferUrl("FACEBOOK", "https://www.facebook.com/marketplace/item/123"),
    ).toContain("facebook.com");
    expect(
      safeOfferUrl(
        "ALLEGRO_LOKALNIE",
        "https://allegrolokalnie.pl/oferta/test",
      ),
    ).toContain("allegrolokalnie.pl");
  });
  it.each([
    "javascript:alert(1)",
    "http://olx.pl/test",
    "https://olx.pl.evil.test/x",
    "https://user:pass@www.olx.pl/x",
    "https://www.olx.pl:8443/x",
    "//www.olx.pl/x",
  ])("does not open the invalid offer URL %s", (value) => {
    expect(safeOfferUrl("OLX", value)).toBeNull();
  });
  it("recognizes old detail keys as the same saved snapshot", () => {
    expect(savedKeyFor(card, new Set(["listing:snap-25"]))).toBe(
      "listing:snap-25",
    );
    expect(savedKeyFor(card, new Set(["snap-25"]))).toBe("snap-25");
    expect(
      savedKeyFor({ ...card, listingId: 101 }, new Set(["listing:101"])),
    ).toBe("listing:101");
    expect(savedKeyFor(card, new Set(["snap-99"]))).toBeNull();
  });
  it("resolves saved detail routes without accepting arbitrary destinations", () => {
    expect(savedOfferId("listing:snap-25")).toBe("snap-25");
    expect(savedOfferId("listing:101")).toBe("101");
    expect(savedOfferId("DEMO:CAR:1", true)).toBe("demo-car-1");
    expect(savedOfferId("DEMO:CAR:1")).toBeNull();
    expect(savedOfferId("https://evil.test")).toBeNull();
    expect(savedOfferId("snap--25")).toBeNull();
  });
});

describe("Observation timestamps", () => {
  it("does not call future, stale or malformed observations fresh", () => {
    const now = Date.parse("2026-10-16T12:00:00Z");
    expect(checkedRecently(card.verifiedAt, now)).toBe(true);
    expect(checkedRecently("2026-10-17T12:00:00Z", now)).toBe(false);
    expect(checkedRecently("2026-10-14T12:00:00Z", now)).toBe(false);
    expect(checkedRecently("INVALID_DATE", now)).toBe(false);
    expect(formatUserDateTime("INVALID_DATE")).toBe("—");
    expect(formatRelativeSync("INVALID_DATE")).toBe("—");
  });
});
