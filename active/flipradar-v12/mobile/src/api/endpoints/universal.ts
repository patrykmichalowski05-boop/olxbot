import { apiRequest } from '@/api/client';

export type UniversalWatchItem = {
  listing_key: string;
  label: string;
  updated: string;
  price_minor?: number | null;
  threshold_minor?: number | null;
};

export type ManualAnalysisInput = {
  external_id: string;
  title: string;
  price: string;
  category: 'ELECTRONICS' | 'CAR' | 'FASHION';
  description?: string;
};

export type ManualAnalysisResult = {
  decision: string;
  reasons?: string[];
  notification_queued?: boolean;
  listing_id?: number;
  snapshot_id?: number;
};

export async function fetchWatchlist(): Promise<UniversalWatchItem[]> {
  const response = await apiRequest<{ items: UniversalWatchItem[] }>(
    '/api/v1/universal/watchlist',
  );
  return response.items ?? [];
}

export async function addWatchItem(key: string, label: string): Promise<void> {
  await apiRequest('/api/v1/universal/watchlist', {
    method: 'POST',
    body: JSON.stringify({ key, label }),
  });
}

export async function closeWatchItem(key: string): Promise<void> {
  await apiRequest('/api/v1/universal/watchlist/close', {
    method: 'POST',
    body: JSON.stringify({ key }),
  });
}

export async function analyzeManual(
  data: ManualAnalysisInput,
): Promise<ManualAnalysisResult> {
  return apiRequest<ManualAnalysisResult>('/api/v1/universal/manual/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
