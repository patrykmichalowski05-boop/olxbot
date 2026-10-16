import type { SavedSearch } from "@/api/endpoints/searches";
import type { OpportunityCard } from "@/features/opportunity/types";
import {
  hasUsableComparison,
  priceAssessment,
  priceLabel,
} from "@/features/workspace/presentation";
import { filterSearchResults } from "@/features/workspace/searchResults";

const profile: SavedSearch = {
  id: "search-1",
  name: "Komputer gamingowy",
  query: "komputer gamingowy",
  platforms: ["OLX", "FACEBOOK"],
  category: "ELECTRONICS",
  purpose: "flip",
  max_price_minor: 300000,
  min_profit_minor: 30000,
  min_roi_bps: 2000,
  enabled: true,
  notify_initial: false,
  excluded_terms: [],
  costs: {
    shipping_minor: 2000,
    repairs_minor: 0,
    travel_minor: 0,
    other_minor: 0,
    sale_fee_bps: 0,
    reserve_bps: 500,
  },
};
const offer: OpportunityCard = {
  id: "snap-1",
  snapshotId: 1,
  title: "Komputer gamingowy",
  platform: "OLX",
  purchaseMinor: 75000,
  operatingProfitMinor: 80000,
  roiBps: 7500,
  decision: "WATCH",
  verifiedAt: null,
  url: null,
  category: "ELECTRONICS",
  sourceStatus: "UNKNOWN",
  hasValuation: true,
  market: {
    status: "OK",
    medianMinor: 299900,
    lowMinor: 185000,
    highMinor: 439900,
    sampleCount: 285,
    confidence: "LOW",
    kind: "ASKING",
  },
};

describe("Saved search display scope", () => {
  it("keeps selected platforms and inclusive budget without rewriting server results", () => {
    const input = [
      offer,
      { ...offer, id: "facebook", platform: "FACEBOOK", purchaseMinor: 300000 },
      { ...offer, id: "too-expensive", purchaseMinor: 300001 },
      { ...offer, id: "other-platform", platform: "VINTED" },
      { ...offer, id: "unknown-price", purchaseMinor: null },
    ];
    const result = filterSearchResults(input, profile);
    expect(result.map((item) => item.id)).toEqual(["snap-1", "facebook"]);
    expect(result[0]).toBe(offer);
    expect(result[0].decision).toBe("WATCH");
    expect(input).toHaveLength(5);
  });
  it("keeps unknown prices when the profile has no budget cap", () => {
    const result = filterSearchResults([{ ...offer, purchaseMinor: null }], {
      ...profile,
      max_price_minor: null,
    });
    expect(result).toHaveLength(1);
  });
  it("does not display unrelated radar offers before a profile is resolved", () => {
    expect(filterSearchResults([offer], undefined)).toEqual([]);
  });
  it("supports all-platform profiles and case-insensitive platform labels", () => {
    expect(
      filterSearchResults([{ ...offer, platform: "olx" }], profile),
    ).toHaveLength(1);
    expect(
      filterSearchResults([{ ...offer, platform: "VINTED" }], {
        ...profile,
        platforms: [],
      }),
    ).toHaveLength(1);
  });
});

describe("Comparable group visibility", () => {
  it("requires a successful estimate, a median and at least three comparisons", () => {
    expect(hasUsableComparison(offer)).toBe(true);
    expect(hasUsableComparison({ ...offer, market: undefined })).toBe(false);
    expect(
      hasUsableComparison({
        ...offer,
        market: { ...offer.market!, status: "NO_RELIABLE_VALUATION" },
      }),
    ).toBe(false);
    expect(
      hasUsableComparison({
        ...offer,
        market: { ...offer.market!, medianMinor: null },
      }),
    ).toBe(false);
    expect(
      hasUsableComparison({
        ...offer,
        market: { ...offer.market!, sampleCount: 2 },
      }),
    ).toBe(false);
  });
  it.each([-1, 0, 0.5, Infinity, NaN])(
    "does not label invalid purchase price %s as a bargain",
    (purchaseMinor) => {
      expect(
        priceAssessment({ ...offer, purchaseMinor }).discountPercent,
      ).toBeNull();
    },
  );
  it("does not render malformed currency values as real amounts", () => {
    expect(priceLabel(Infinity)).toBe("—");
    expect(priceLabel(2.5)).toBe("—");
    expect(priceLabel(75000)).toContain("750");
  });
});
