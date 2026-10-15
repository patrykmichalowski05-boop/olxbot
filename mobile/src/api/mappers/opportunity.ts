import type { ListingSummary } from '@/api/types/listings';
import type { RadarApiItem } from '@/api/types/radar';
import type { CategoryTabId } from '@/utils/labels';
import type {
  OpportunityCard,
  OpportunityDetail,
} from '@/features/opportunity/types';

function inferCategory(
  title: string | null,
  valuation: Record<string, unknown>,
): CategoryTabId {
  const cat = String(valuation.category ?? valuation.product_category ?? '').toUpperCase();
  if (cat.includes('CAR') || cat.includes('AUTO')) return 'CAR';
  if (cat.includes('FASHION') || cat.includes('MODA')) return 'FASHION';
  if (cat.includes('ELECTRON')) return 'ELECTRONICS';

  const text = (title ?? '').toLowerCase();
  if (/(bmw|audi|volkswagen|skoda|toyota|ford|mercedes)/.test(text)) return 'CAR';
  if (/(iphone|rtx|gpu|laptop|playstation|xbox|macbook)/.test(text)) return 'ELECTRONICS';
  if (/(nike|adidas|buty|rozmiar|bluza|kurtka)/.test(text)) return 'FASHION';
  return 'OTHER';
}

function valuationNumber(valuation: Record<string, unknown>, key: string): number | null {
  const value = valuation[key];
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.round(value * 100);
  }
  return null;
}

function pickRisk(valuation: Record<string, unknown>): string | undefined {
  const issues = valuation.ai_issues;
  if (Array.isArray(issues) && typeof issues[0] === 'string') {
    return issues[0];
  }
  const missing = valuation.ai_missing_info;
  if (Array.isArray(missing) && typeof missing[0] === 'string') {
    return `Brak: ${missing[0]}`;
  }
  return undefined;
}

function hasReliableValuation(
  decision: string,
  valuation: Record<string, unknown>,
): boolean {
  if (decision.toUpperCase() === 'NO_RELIABLE_VALUATION') {
    return false;
  }
  if (valuation.ok === false) {
    return false;
  }
  return (
    valuationNumber(valuation, 'quick_sale') !== null ||
    valuationNumber(valuation, 'static_quick_sale') !== null
  );
}

export function mapRadarItem(item: RadarApiItem): OpportunityCard {
  const valuation = item.valuation ?? {};
  const quick = valuationNumber(valuation, 'quick_sale');
  const profit =
    typeof valuation.profit === 'number'
      ? Math.round(valuation.profit * 100)
      : quick !== null && item.price_minor !== null
        ? quick - item.price_minor
        : null;

  let roiBps: number | null = null;
  if (
    profit !== null &&
    item.price_minor !== null &&
    item.price_minor > 0
  ) {
    roiBps = Math.round((profit / item.price_minor) * 10_000);
  }

  const decision = String(item.decision ?? 'UNKNOWN').toUpperCase();

  return {
    id: `snap-${item.snapshot_id}`,
    snapshotId: item.snapshot_id,
    title: item.title?.trim() || 'Oferta bez tytułu',
    platform: item.platform,
    purchaseMinor: item.price_minor,
    resaleRange: quick !== null ? { lowMinor: quick, highMinor: quick } : undefined,
    operatingProfitMinor: profit,
    roiBps,
    decision,
    confidence:
      typeof valuation.confidence === 'string'
        ? valuation.confidence
        : typeof valuation.ai_confidence === 'number'
          ? `${Math.round(valuation.ai_confidence * 100)}%`
          : undefined,
    topRisk: pickRisk(valuation),
    insight: typeof valuation.ai_summary === 'string' ? valuation.ai_summary : undefined,
    imageUrl: typeof valuation.image_url === 'string' ? valuation.image_url : null,
    verifiedAt: item.observed_at,
    url: item.url,
    category: inferCategory(item.title, valuation),
    sourceStatus: item.source_status ?? 'UNKNOWN',
    hasValuation: hasReliableValuation(decision, valuation),
  };
}

export function mapListingDetail(listing: ListingSummary): OpportunityDetail {
  const analysis = listing.current_analysis;
  const valuation = (analysis?.valuation ?? {}) as Record<string, unknown>;
  const decisionRaw =
    typeof analysis?.decision === 'string'
      ? analysis.decision
      : String(
          (analysis?.decision as Record<string, unknown> | undefined)?.action ??
            (analysis?.decision as Record<string, unknown> | undefined)?.decision ??
            'UNKNOWN',
        );

  const card = mapRadarItem({
    snapshot_id: analysis?.snapshot_id ?? listing.id,
    decision: decisionRaw,
    valuation,
    observed_at: listing.created_at ?? null,
    title: listing.title,
    platform: listing.platform,
    price_minor: listing.price_minor,
    url: listing.url,
    source_status: listing.source_status,
  });

  const risks: string[] = [];
  if (Array.isArray(valuation.ai_issues)) {
    for (const issue of valuation.ai_issues) {
      if (typeof issue === 'string') risks.push(issue);
    }
  }

  const unknowns: string[] = [];
  if (Array.isArray(valuation.ai_missing_info)) {
    for (const item of valuation.ai_missing_info) {
      if (typeof item === 'string') unknowns.push(item);
    }
  }

  const purchaseMinor = listing.price_minor;
  const resaleMinor = valuationNumber(valuation, 'quick_sale');
  const costsMinor = valuationNumber(valuation, 'total_cost');

  return {
    ...card,
    listingId: listing.id,
    valuation,
    decisionReason:
      typeof valuation.ai_summary === 'string' ? valuation.ai_summary : undefined,
    risks,
    unknowns,
    dataQuality:
      typeof valuation.confidence === 'string' ? valuation.confidence : undefined,
    specs: [],
    comparisons: [],
    priceHistory: [],
    conservativeScenario: {
      label: 'Konserwatywny',
      purchaseMinor,
      resaleMinor:
        valuationNumber(valuation, 'neighbor_quick_protected') ?? resaleMinor,
      costsMinor,
      profitMinor: null,
      roiBps: null,
    },
    baseScenario: {
      label: 'Bazowy',
      purchaseMinor,
      resaleMinor,
      costsMinor,
      profitMinor: card.operatingProfitMinor,
      roiBps: card.roiBps,
    },
    maxBuyMinor:
      typeof valuation.max_buy === 'number'
        ? Math.round(valuation.max_buy * 100)
        : null,
  };
}


export function mapSnapshotDetail(item: RadarApiItem): OpportunityDetail {
  const card = mapRadarItem(item);
  const valuation = item.valuation ?? {};
  const strings = (key: string): string[] => {
    const value = valuation[key];
    return Array.isArray(value)
      ? value.filter((x): x is string => typeof x === 'string')
      : [];
  };

  return {
    ...card,
    valuation,
    decisionReason:
      typeof valuation.ai_summary === 'string'
        ? valuation.ai_summary : undefined,
    risks: strings('ai_issues'),
    unknowns: strings('ai_missing_info'),
    dataQuality: card.confidence,
    specs: [],
    comparisons: [],
    priceHistory: [],
    baseScenario: {
      label: 'Bazowy',
      purchaseMinor: card.purchaseMinor,
      resaleMinor: card.resaleRange?.highMinor ?? null,
      costsMinor: valuationNumber(valuation, 'total_cost'),
      profitMinor: card.operatingProfitMinor,
      roiBps: card.roiBps,
    },
    maxBuyMinor: valuationNumber(valuation, 'max_buy'),
  };
}
