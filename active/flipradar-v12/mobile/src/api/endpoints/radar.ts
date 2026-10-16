import { apiRequest } from '@/api/client';
import { radarSource } from '@/utils/config';
import type { RadarApiItem, RadarPageResponse } from '@/api/types/radar';

export type RadarQuery = {
  limit?: number;
  beforeId?: number | null;
  q?: string;
  signal?: AbortSignal;
};

export async function fetchRadarPage(query: RadarQuery): Promise<RadarPageResponse> {
  const limit = query.limit ?? 30;
  const pathBase =
    radarSource() === 'universal'
      ? '/api/v1/universal/mobile-radar'
      : '/api/v1/radar';

  const params = new URLSearchParams();
  params.set('limit', String(limit));
  if (query.beforeId) {
    params.set('before_id', String(query.beforeId));
  }
  if (query.q?.trim()) {
    params.set('q', query.q.trim().slice(0, 120));
  }

  return apiRequest<RadarPageResponse>(`${pathBase}?${params.toString()}`, {
    signal: query.signal,
  });
}


export async function fetchRadarSnapshot(
  snapshotId: number,
): Promise<RadarApiItem> {
  if (!Number.isSafeInteger(snapshotId) || snapshotId <= 0) {
    throw new Error('Nieprawidłowy snapshot ID');
  }
  return apiRequest<RadarApiItem>(
    `/api/v1/universal/mobile-radar/${snapshotId}`,
  );
}
