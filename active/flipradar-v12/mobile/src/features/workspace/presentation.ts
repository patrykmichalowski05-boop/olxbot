import type {
  MarketEvidence,
  OpportunityCard,
} from "@/features/opportunity/types";
import type { BadgeTone } from "@/components/Badge";

export const platformNames: Record<string, string> = {
  OLX: "OLX",
  FACEBOOK: "Facebook",
  ALLEGRO_LOKALNIE: "Allegro Lokalnie",
  ALLEGRO: "Allegro",
  OTOMOTO: "Otomoto",
  VINTED: "Vinted",
  MANUAL: "Własne",
};

export function platformName(value: string) {
  return platformNames[value.toUpperCase()] ?? "Inne źródło";
}

export function priceLabel(value: number | null | undefined) {
  if (value == null || !Number.isSafeInteger(value)) return "—";
  return `${(value / 100).toLocaleString("pl-PL", { maximumFractionDigits: 2 })} zł`;
}

const positiveMinor = (value: unknown) =>
  typeof value === "number" && Number.isSafeInteger(value) && value > 0
    ? value
    : null;

export function readMarket(value: unknown): MarketEvidence | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value))
    return undefined;
  const row = value as Record<string, unknown>;
  return {
    medianMinor: positiveMinor(row.median_minor),
    lowMinor: positiveMinor(row.low_minor),
    highMinor: positiveMinor(row.high_minor),
    sampleCount:
      typeof row.sample_count === "number" &&
      Number.isSafeInteger(row.sample_count) &&
      row.sample_count >= 0
        ? row.sample_count
        : null,
    confidence: typeof row.confidence === "string" ? row.confidence : null,
    kind: typeof row.kind === "string" ? row.kind : null,
    status: typeof row.status === "string" ? row.status : null,
  };
}

export function hasUsableComparison(item: OpportunityCard): boolean {
  const market = item.market;
  return (
    market?.status === "OK" &&
    market.medianMinor !== null &&
    Number.isSafeInteger(market.medianMinor) &&
    market.medianMinor > 0 &&
    market.sampleCount !== null &&
    Number.isSafeInteger(market.sampleCount) &&
    market.sampleCount >= 3
  );
}

export function priceAssessment(item: OpportunityCard): {
  label: string;
  tone: BadgeTone;
  discountPercent: number | null;
} {
  const median = item.market?.medianMinor;
  if (
    !hasUsableComparison(item) ||
    !median ||
    !item.purchaseMinor ||
    !Number.isSafeInteger(item.purchaseMinor) ||
    item.purchaseMinor <= 0
  ) {
    return { label: "Brak oceny ceny", tone: "neutral", discountPercent: null };
  }
  const discount = Math.round(((median - item.purchaseMinor) / median) * 100);
  if (discount >= 50)
    return {
      label: "Podejrzanie tanio",
      tone: "warning",
      discountPercent: discount,
    };
  if (discount >= 15)
    return { label: "Dobra cena", tone: "success", discountPercent: discount };
  if (discount < -15)
    return {
      label: "Powyżej typowej ceny",
      tone: "neutral",
      discountPercent: discount,
    };
  return { label: "Cena typowa", tone: "neutral", discountPercent: discount };
}

export function priceAssessmentText(item: OpportunityCard) {
  const assessment = priceAssessment(item);
  const discount = assessment.discountPercent;
  if (discount === null) return "—";
  if (discount > 0) return `o ${discount}% poniżej typowej ceny`;
  if (discount < 0) return `o ${Math.abs(discount)}% powyżej typowej ceny`;
  return "Na poziomie typowej ceny";
}

export function confidenceLabel(value: string | null | undefined) {
  const upper = value?.toUpperCase();
  if (upper === "HIGH") return "wysoka";
  if (upper === "MEDIUM") return "umiarkowana";
  if (upper === "LOW") return "ograniczona";
  if (value && /^\d{1,3}%$/.test(value) && parseInt(value, 10) <= 100)
    return value;
  return "—";
}

export function offerTags(item: OpportunityCard) {
  const explicit = [item.variant, item.modelLabel, item.conditionLabel].filter(
    (v): v is string => Boolean(v),
  );
  const matches =
    item.title.match(
      /(?:RTX\s?\d{4}(?:\s?Ti)?(?:\s?SUPER)?(?:\s?\d{1,2}\s?GB)?|GTX\s?\d{3,4}(?:\s?Ti)?|RX\s?\d{4}(?:\s?XT)?|i[3579]-?\d{4,5}[A-Z]*|Ryzen\s?[3579](?:\s?\d{4}[A-Z]*)?|\d{1,3}\s?GB\s?RAM|\d(?:[.,]\d)?\s?TB\s?SSD|\d{3,4}\s?GB\s?SSD|\d{2,3}\s?Hz)/gi,
    ) ?? [];
  return [...new Set([...explicit, ...matches])].slice(0, 5);
}

export function safeOfferUrl(
  platform: string,
  value: string | null | undefined,
) {
  if (!value) return null;
  const hosts: Record<string, string[]> = {
    OLX: ["olx.pl"],
    FACEBOOK: ["facebook.com"],
    ALLEGRO_LOKALNIE: ["allegrolokalnie.pl"],
    ALLEGRO: ["allegro.pl", "allegrolokalnie.pl"],
    OTOMOTO: ["otomoto.pl"],
    VINTED: ["vinted.pl", "vinted.com"],
  };
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      (url.port && url.port !== "443")
    )
      return null;
    return hosts[platform.toUpperCase()]?.some(
      (host) => url.hostname === host || url.hostname.endsWith("." + host),
    )
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

/** Statistics describe the loaded asking prices, never a whole marketplace. */
export function loadedPriceSummary(items: OpportunityCard[]) {
  const prices = items
    .flatMap((item) =>
      item.purchaseMinor !== null &&
      Number.isSafeInteger(item.purchaseMinor) &&
      item.purchaseMinor > 0
        ? [item.purchaseMinor]
        : [],
    )
    .sort((a, b) => a - b);
  const middle = Math.floor(prices.length / 2);
  const median = prices.length
    ? prices.length % 2
      ? prices[middle]
      : Math.round((prices[middle - 1] + prices[middle]) / 2)
    : null;
  const validDates = items
    .map((item) => item.verifiedAt)
    .filter(
      (value): value is string =>
        Boolean(value) && Number.isFinite(Date.parse(value!)),
    );
  const latestAt =
    validDates.sort((a, b) => Date.parse(b) - Date.parse(a))[0] ?? null;
  return {
    count: items.length,
    pricedCount: prices.length,
    medianMinor: median,
    lowMinor: prices.length
      ? prices[Math.floor((prices.length - 1) / 4)]
      : null,
    highMinor: prices.length
      ? prices[Math.floor((3 * (prices.length - 1)) / 4)]
      : null,
    minMinor: prices[0] ?? null,
    maxMinor: prices[prices.length - 1] ?? null,
    latestAt,
  };
}

export function checkedRecently(date: string | null, now = Date.now()) {
  const timestamp = date ? Date.parse(date) : NaN;
  return (
    Number.isFinite(timestamp) && now >= timestamp && now - timestamp < 86400000
  );
}

export function savedKeyFor(item: OpportunityCard, keys: ReadonlySet<string>) {
  return (
    [
      item.id,
      `listing:${item.id}`,
      ...(item.listingId ? [`listing:${item.listingId}`] : []),
    ].find((key) => keys.has(key)) ?? null
  );
}

export function savedOfferId(key: string, demo = false): string | null {
  const normalized = key.replace(/^listing:/, "");
  if (/^(?:snap-[1-9]\d*|[1-9]\d*)$/.test(normalized)) return normalized;
  if (demo && /^demo-[a-z0-9-]{1,70}$/.test(normalized)) return normalized;
  if (demo && /^DEMO:(CAR|FASHION):[1-9]\d*$/.test(key)) {
    const [, category, id] = key.split(":");
    return `demo-${category === "FASHION" ? "shoe" : "car"}-${id}`;
  }
  return null;
}
