export type BackendCapabilities = {
  backend: string;
  read_only: boolean;
  search_platforms: string[];
  search_categories: string[];
  search_purposes: string[];
  watchlist: boolean;
  manual_analysis: boolean;
  deals: boolean;
  deals_read: boolean;
  private_searches: boolean;
  radar_scope: string;
  market_valuation: boolean;
  public_search: boolean;
  plan_requests: boolean;
  admin_access: boolean;
  account_delete: boolean;
};

export const fullCapabilities: BackendCapabilities = {
  backend: "universal",
  read_only: false,
  search_platforms: [
    "OLX",
    "FACEBOOK",
    "ALLEGRO_LOKALNIE",
    "OTOMOTO",
    "VINTED",
  ],
  search_categories: ["ELECTRONICS", "CAR", "FASHION", "OTHER"],
  search_purposes: ["flip", "cheap"],
  deals_read: true,
  private_searches: true,
  radar_scope: "private",
  watchlist: true,
  manual_analysis: true,
  deals: true,
  market_valuation: true,
  public_search: true,
  plan_requests: true,
  admin_access: true,
  account_delete: false,
};
export const flaskCapabilities: BackendCapabilities = {
  backend: "flask-v12",
  read_only: false,
  search_platforms: ["OLX"],
  search_categories: ["gpu", "pc", "phone", "laptop", "other"],
  search_purposes: ["cheap"],
  deals_read: false,
  private_searches: true,
  radar_scope: "private",
  watchlist: false,
  manual_analysis: false,
  deals: false,
  market_valuation: false,
  public_search: false,
  plan_requests: false,
  admin_access: false,
  account_delete: true,
};

/** Existing universal APIs omit capabilities; V12 builds use a conservative fallback. */
export function readCapabilities(
  value: unknown,
  flask = false,
): BackendCapabilities {
  const fallback = flask ? flaskCapabilities : fullCapabilities;
  if (!value || typeof value !== "object" || Array.isArray(value))
    return fallback;
  const row = value as Record<string, unknown>;
  const flags = Object.fromEntries(
    [
      "watchlist",
      "manual_analysis",
      "deals",
      "deals_read",
      "private_searches",
      "market_valuation",
      "public_search",
      "plan_requests",
      "admin_access",
      "account_delete",
    ].map((key) => [key, row[key] === true]),
  );
  const strings = (key: string) =>
    Array.isArray(row[key])
      ? (row[key] as unknown[]).filter(
          (item): item is string => typeof item === "string",
        )
      : [];
  return {
    ...fallback,
    ...flags,
    backend: typeof row.backend === "string" ? row.backend : fallback.backend,
    read_only: row.read_only === true,
    radar_scope: row.radar_scope === "global" ? "global" : "private",
    search_platforms: strings("search_platforms"),
    search_categories: strings("search_categories"),
    search_purposes: strings("search_purposes"),
  };
}
