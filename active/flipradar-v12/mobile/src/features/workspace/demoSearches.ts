import type { SavedSearch } from "@/api/endpoints/searches";

function exampleSearch(id: string, name: string, query: string): SavedSearch {
  return {
    id,
    name,
    query,
    platforms: ["OLX", "FACEBOOK"],
    category: "ELECTRONICS",
    purpose: "flip",
    max_price_minor: null,
    min_profit_minor: 30000,
    min_roi_bps: 2000,
    enabled: true,
    notify_initial: false,
    excluded_terms: ["uszkodzony"],
    reference_days: 14,
    costs: {
      shipping_minor: 2000,
      repairs_minor: 0,
      travel_minor: 0,
      other_minor: 0,
      sale_fee_bps: 0,
      reserve_bps: 500,
    },
  };
}
let searches: SavedSearch[] = [
  exampleSearch("demo-computer", "Komputer gamingowy", "komputer gamingowy"),
  exampleSearch("demo-gpu", "RTX 4070", "RTX 4070"),
];

export const demoSearches = {
  async list() {
    return [...searches];
  },
  async save(search: SavedSearch) {
    searches = [search, ...searches.filter((row) => row.id !== search.id)];
    return search;
  },
  async remove(id: string) {
    searches = searches.filter((row) => row.id !== id);
  },
};
