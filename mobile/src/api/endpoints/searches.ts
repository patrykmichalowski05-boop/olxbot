import { apiRequest } from "@/api/client";

export const searchPlatforms = [
  "OLX",
  "FACEBOOK",
  "ALLEGRO_LOKALNIE",
  "OTOMOTO",
  "VINTED",
] as const;
export type SearchPlatform = (typeof searchPlatforms)[number];
export type SavedSearch = {
  id: string;
  name: string;
  query: string;
  platforms: SearchPlatform[];
  category: string;
  purpose: "flip" | "cheap";
  max_price_minor: number | null;
  min_profit_minor: number;
  min_roi_bps: number;
  enabled: boolean;
  notify_initial: boolean;
  excluded_terms: string[];
  costs: {
    shipping_minor: number;
    repairs_minor: number;
    travel_minor: number;
    other_minor: number;
    sale_fee_bps: number;
    reserve_bps: number;
  };
  [key: string]: unknown;
};
export type SourceHealth = {
  search_id: string;
  platform: SearchPlatform;
  status: string;
  message: string;
  checked_at: string;
  count: number;
};
export async function getSearches(signal?: AbortSignal) {
  const response = await apiRequest<{ items: SavedSearch[] }>(
    "/api/v1/universal/searches",
    { signal },
  );
  return response.items;
}
export async function saveSearch(
  search: Partial<SavedSearch> & Pick<SavedSearch, "id" | "name" | "query">,
) {
  return apiRequest<SavedSearch>(
    `/api/v1/universal/searches/${encodeURIComponent(search.id)}`,
    {
      method: "PUT",
      body: JSON.stringify(search),
    },
  );
}
export async function getSourceHealth(signal?: AbortSignal) {
  return apiRequest<{
    items: SourceHealth[];
    notifications: Record<string, number>;
  }>("/api/v1/universal/source-health", { signal });
}
