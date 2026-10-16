import AsyncStorage from "@react-native-async-storage/async-storage";

import type { CategoryTabId } from "@/utils/labels";

export type RadarFilters = {
  query: string;
  category: CategoryTabId;
  minProfitMinor: number | null;
  minRoiBps: number | null;
  maxBudgetMinor: number | null;
  minBudgetMinor?: number | null;
  platforms: string[];
  sort: "fresh" | "profit" | "roi" | "price" | "quality";
};

export const defaultFilters: RadarFilters = {
  query: "",
  category: "ALL",
  minProfitMinor: null,
  minRoiBps: null,
  maxBudgetMinor: null,
  minBudgetMinor: null,
  platforms: [],
  sort: "fresh",
};

const KEY = "flipradar_filters_v1";
const PROFILES_KEY = "flipradar_filter_profiles_v1";

export type SavedFilterProfile = {
  id: string;
  name: string;
  filters: RadarFilters;
};

export async function loadFilters(): Promise<RadarFilters> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return defaultFilters;
    return { ...defaultFilters, ...(JSON.parse(raw) as RadarFilters) };
  } catch {
    return defaultFilters;
  }
}

export async function saveFilters(filters: RadarFilters) {
  await AsyncStorage.setItem(KEY, JSON.stringify(filters));
}

export async function loadProfiles(): Promise<SavedFilterProfile[]> {
  try {
    const raw = await AsyncStorage.getItem(PROFILES_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as SavedFilterProfile[];
  } catch {
    return [];
  }
}

export async function saveProfiles(profiles: SavedFilterProfile[]) {
  await AsyncStorage.setItem(PROFILES_KEY, JSON.stringify(profiles));
}

export function countActiveFilters(filters: RadarFilters): number {
  let count = 0;
  if (filters.category !== "ALL") count += 1;
  if (filters.minProfitMinor !== null) count += 1;
  if (filters.minRoiBps !== null) count += 1;
  if (filters.maxBudgetMinor !== null) count += 1;
  if (filters.minBudgetMinor != null) count += 1;
  if (filters.platforms.length > 0) count += 1;
  if (filters.sort !== "fresh") count += 1;
  return count;
}

export function applyClientFilters<
  T extends {
    category: CategoryTabId;
    purchaseMinor: number | null;
    operatingProfitMinor: number | null;
    roiBps: number | null;
    platform: string;
    hasValuation: boolean;
  },
>(items: T[], filters: RadarFilters): T[] {
  let result = items;

  if (filters.category !== "ALL") {
    result = result.filter((item) => item.category === filters.category);
  }

  if (filters.maxBudgetMinor !== null) {
    result = result.filter(
      (item) =>
        item.purchaseMinor !== null &&
        item.purchaseMinor <= filters.maxBudgetMinor!,
    );
  }

  if (filters.minBudgetMinor != null) {
    result = result.filter(
      (item) =>
        item.purchaseMinor !== null &&
        item.purchaseMinor >= filters.minBudgetMinor!,
    );
  }

  if (filters.minProfitMinor !== null) {
    result = result.filter(
      (item) =>
        item.operatingProfitMinor !== null &&
        item.operatingProfitMinor >= filters.minProfitMinor!,
    );
  }

  if (filters.minRoiBps !== null) {
    result = result.filter(
      (item) => item.roiBps !== null && item.roiBps >= filters.minRoiBps!,
    );
  }

  if (filters.platforms.length > 0) {
    const set = new Set(filters.platforms.map((p) => p.toUpperCase()));
    result = result.filter((item) => set.has(item.platform.toUpperCase()));
  }

  switch (filters.sort) {
    case "profit":
      result = [...result].sort(
        (a, b) =>
          (b.operatingProfitMinor ?? -1) - (a.operatingProfitMinor ?? -1),
      );
      break;
    case "roi":
      result = [...result].sort((a, b) => (b.roiBps ?? -1) - (a.roiBps ?? -1));
      break;
    case "price":
      result = [...result].sort(
        (a, b) =>
          (a.purchaseMinor ?? Number.MAX_SAFE_INTEGER) -
          (b.purchaseMinor ?? Number.MAX_SAFE_INTEGER),
      );
      break;
    case "quality":
      result = [...result].sort(
        (a, b) => Number(b.hasValuation) - Number(a.hasValuation),
      );
      break;
    default:
      break;
  }

  return result;
}
