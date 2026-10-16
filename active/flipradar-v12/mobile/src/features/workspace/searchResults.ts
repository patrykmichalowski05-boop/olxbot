import type { SavedSearch } from "@/api/endpoints/searches";
import type { OpportunityCard } from "@/features/opportunity/types";

/** The existing radar endpoint searches text; apply the profile's display scope locally. */
export function filterSearchResults(
  items: OpportunityCard[],
  profile: SavedSearch | undefined,
): OpportunityCard[] {
  if (!profile) return [];
  const platforms = new Set(
    profile.platforms.map((value) => value.toUpperCase()),
  );
  return items.filter(
    (item) =>
      (!platforms.size || platforms.has(item.platform.toUpperCase())) &&
      (profile.max_price_minor === null ||
        (item.purchaseMinor !== null &&
          item.purchaseMinor <= profile.max_price_minor)),
  );
}
