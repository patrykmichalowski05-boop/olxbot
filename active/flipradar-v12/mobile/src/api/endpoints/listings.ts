import { apiRequest } from '@/api/client';
import type {
  ListingSummary,
  ListingsPageResponse,
  PriceHistoryEntry,
} from '@/api/types/listings';

export async function fetchListing(id: number): Promise<ListingSummary> {
  return apiRequest<ListingSummary>(`/api/v1/listings/${id}`);
}

export async function fetchListingHistory(
  id: number,
): Promise<PriceHistoryEntry[]> {
  const response = await apiRequest<{ items: PriceHistoryEntry[] }>(
    `/api/v1/listings/${id}/history`,
  );
  return response.items ?? [];
}

export async function fetchListingsPage(query: {
  limit?: number;
  beforeId?: number | null;
  q?: string;
}): Promise<ListingsPageResponse> {
  const params = new URLSearchParams();
  params.set('limit', String(query.limit ?? 30));
  if (query.beforeId) {
    params.set('before_id', String(query.beforeId));
  }
  if (query.q?.trim()) {
    params.set('q', query.q.trim().slice(0, 120));
  }
  return apiRequest<ListingsPageResponse>(`/api/v1/listings?${params.toString()}`);
}
