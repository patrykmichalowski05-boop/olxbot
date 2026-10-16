import type { OpportunityDetail } from "@/features/opportunity/types";

// Synthetic examples for the UI. No record represents an actual marketplace ad.
const examples: [string, number, number, string][] = [
  [
    "Komputer gamingowy i5-12400F / RTX 3060 Ti / 32 GB RAM / 1 TB SSD + monitor 165 Hz",
    309900,
    399900,
    "FACEBOOK",
  ],
  ["CyberPowerPC Gamer Xtreme VR i5-13400F / 1 TB SSD", 47900, 299900, "OLX"],
  ["Acer Nitro 16 Ryzen 5 / RTX 4060 / 1 TB SSD", 360000, 359900, "OLX"],
  [
    "Laptop Dell G15 Ryzen 5000 edition / RTX 3050 / gwarancja",
    220000,
    299900,
    "OLX",
  ],
  ["PC RTX 4060 8 GB / i5-10400F", 270000, 289900, "OLX"],
  [
    "Laptop HP Victus 15 / Ryzen 5 8645HS / 16 GB RAM / 512 GB SSD / RTX 3050 6 GB",
    234900,
    319900,
    "OLX",
  ],
  [
    "Komputer gamingowy i5 / GTX 1630 4 GB / 8 GB / 120+500 GB / Windows 11 Pro",
    75000,
    299900,
    "OLX",
  ],
  [
    "Komputer gamingowy i5 / GTX 970 4 GB / 8 GB / 120+500 GB SSD + HDD",
    75000,
    299900,
    "OLX",
  ],
];

export const workspaceDemoOffers: OpportunityDetail[] = examples.map(
  ([title, price, median, platform], index) => {
    const resale = Math.round(median * 0.83);
    const costs = 12000;
    const profit = resale - price - costs;
    const roi = Math.round((profit / (price + costs)) * 10000);
    const market = {
      medianMinor: median,
      lowMinor: Math.round(median * 0.85),
      highMinor: Math.round(median * 1.15),
      sampleCount: 24 + index,
      confidence: "LOW",
      status: "OK",
      kind: "ASKING",
    };
    const now = new Date().toISOString();
    return {
      id: `demo-workspace-${index + 1}`,
      snapshotId: 2010 - index,
      listingId: 710 - index,
      title,
      platform,
      category: "ELECTRONICS",
      sourceStatus: "ACTIVE",
      purchaseMinor: price,
      resaleRange: { lowMinor: resale, highMinor: resale },
      operatingProfitMinor: profit,
      roiBps: roi,
      hasValuation: true,
      decision:
        price < median * 0.5 ? "WATCH" : profit > 0 ? "BUY_CANDIDATE" : "SKIP",
      market,
      confidence: "LOW",
      verifiedAt: now,
      url: null,
      imageUrl: null,
      insight:
        "Przykładowe porównanie podobnych wariantów. Przedstawione kwoty służą wyłącznie pokazaniu działania interfejsu.",
      insightSource: "rules",
      topRisk:
        price < median * 0.5
          ? "Duża różnica ceny — sprawdź kompletność zestawu, stan i wiarygodność sprzedawcy."
          : "Ceny ofertowe nie potwierdzają ceny zawartej transakcji.",
      valuation: {
        quick_sale: resale / 100,
        profit: profit / 100,
        total_cost: costs / 100,
        roi_bps: roi,
        market: {
          median_minor: market.medianMinor,
          low_minor: market.lowMinor,
          high_minor: market.highMinor,
          sample_count: market.sampleCount,
          confidence: "LOW",
          status: "OK",
          kind: "ASKING",
        },
      },
      risks: ["Przykładowe dane; stan sprzętu nie był sprawdzany."],
      unknowns: [],
      specs: [],
      comparisons: [],
      priceHistory: [],
      baseScenario: {
        label: "Przykładowy",
        purchaseMinor: price,
        resaleMinor: resale,
        costsMinor: costs,
        profitMinor: profit,
        roiBps: roi,
      },
      maxBuyMinor: null,
    };
  },
);
