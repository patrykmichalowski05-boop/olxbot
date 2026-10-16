import { apiRequest } from "@/api/client";
import { radarSource } from "@/utils/config";
import type { RadarApiItem, RadarPageResponse } from "@/api/types/radar";

export type RadarQuery = {
  limit?: number;
  beforeId?: number | null;
  q?: string;
  signal?: AbortSignal;
  minPriceMinor?: number | null;
  maxPriceMinor?: number | null;
  minProfitMinor?: number | null;
  minRoiBps?: number | null;
  category?: string;
  platforms?: string[];
};

export async function fetchRadarPage(
  query: RadarQuery,
): Promise<RadarPageResponse> {
  const limit = query.limit ?? 30;
  const pathBase =
    radarSource() === "universal"
      ? "/api/v1/universal/mobile-radar"
      : "/api/v1/radar";

  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (query.beforeId) {
    params.set("before_id", String(query.beforeId));
  }
  if (query.q?.trim()) {
    params.set("q", query.q.trim().slice(0, 120));
  }

  for (const [key, value] of [
    ["min_price_minor", query.minPriceMinor],
    ["max_price_minor", query.maxPriceMinor],
    ["min_profit_minor", query.minProfitMinor],
    ["min_roi_bps", query.minRoiBps],
  ] as const) {
    if (value != null) params.set(key, String(value));
  }
  if (query.category && query.category !== "ALL")
    params.set("category", query.category);
  if (query.platforms?.length)
    params.set("platform", query.platforms.join(","));
  return apiRequest<RadarPageResponse>(`${pathBase}?${params.toString()}`, {
    signal: query.signal,
  });
}

export async function fetchRadarSnapshot(
  snapshotId: number,
): Promise<RadarApiItem> {
  if (!Number.isSafeInteger(snapshotId) || snapshotId <= 0) {
    throw new Error("Nieprawidłowy snapshot ID");
  }
  return apiRequest<RadarApiItem>(
    `/api/v1/universal/mobile-radar/${snapshotId}`,
  );
}
