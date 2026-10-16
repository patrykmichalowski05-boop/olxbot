export type ListingSummary = {
  id: number;
  id_type: string;
  offer_key?: string;
  platform: string;
  title: string | null;
  url: string | null;
  price_minor: number | null;
  currency: string;
  score?: number | null;
  created_at?: string | null;
  source_status?: string;
  current_analysis?: {
    valuation: Record<string, unknown>;
    decision: Record<string, unknown> | string;
    snapshot_id?: number;
  } | null;
};

export type ListingsPageResponse = {
  items: ListingSummary[];
  next_before_id: number | null;
};

export type PriceHistoryEntry = {
  observed_at?: string;
  price_minor?: number | null;
  [key: string]: unknown;
};
