import type { CategoryTabId } from '@/utils/labels';

export type OpportunityCard = {
  id: string;
  snapshotId: number;
  listingId?: number;
  title: string;
  brand?: string;
  modelLabel?: string;
  variant?: string;
  platform: string;
  location?: string;
  shipping?: boolean;
  conditionLabel?: string;
  purchaseMinor: number | null;
  resaleRange?: { lowMinor: number | null; highMinor: number | null };
  operatingProfitMinor: number | null;
  roiBps: number | null;
  decision: string;
  confidence?: string;
  topRisk?: string;
  insight?: string;
  verifiedAt: string | null;
  imageUrl?: string | null;
  url: string | null;
  category: CategoryTabId;
  sourceStatus: string;
  hasValuation: boolean;
};

export type OpportunityDetail = OpportunityCard & {
  valuation: Record<string, unknown>;
  decisionReason?: string;
  risks: string[];
  unknowns: string[];
  dataQuality?: string;
  specs: { label: string; value: string; provenance: 'declared' | 'extracted' | 'verified' }[];
  comparisons: MarketComparison[];
  priceHistory: { at: string; priceMinor: number | null; label: string }[];
  conservativeScenario?: FinancialScenario;
  baseScenario?: FinancialScenario;
  maxBuyMinor: number | null;
};

export type MarketComparison = {
  title: string;
  variant?: string;
  condition?: string;
  priceMinor: number | null;
  source: string;
  observedAt: string;
  kind: 'active' | 'sold';
};

export type FinancialScenario = {
  label: string;
  purchaseMinor: number | null;
  resaleMinor: number | null;
  costsMinor: number | null;
  profitMinor: number | null;
  roiBps: number | null;
};
