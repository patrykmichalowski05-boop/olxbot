export type RadarApiItem = {
  snapshot_id: number;
  offer_key?: string;
  decision: string;
  valuation: Record<string, unknown>;
  observed_at: string | null;
  title: string | null;
  platform: string;
  price_minor: number | null;
  url: string | null;
  currency?: string;
  source_status?: string;
};

export type RadarPageResponse = {
  items: RadarApiItem[];
  next_before_id: number | null;
};
