import { apiRequest } from '@/api/client';
import { workspaceId } from '@/utils/config';

function ws(): string {
  const id = workspaceId();
  if (!id) {
    throw new Error('Brak EXPO_PUBLIC_FLIP_WORKSPACE_ID');
  }
  return id;
}

import type { FinancialDeal } from '@/api/mappers/deal';

export type DealSummary = FinancialDeal;

export type DealPage = {
  items: DealSummary[];
  next_before_id?: string | null;
};

export async function fetchDeals(query?: {
  status?: string;
  beforeId?: string | null;
}): Promise<DealPage> {
  const params = new URLSearchParams();
  params.set('limit', '30');
  if (query?.status) params.set('status', query.status);
  if (query?.beforeId) params.set('before_id', query.beforeId);
  return apiRequest<DealPage>(
    `/api/v2/workspaces/${ws()}/deals?${params.toString()}`,
  );
}

export async function fetchDeal(dealId: string): Promise<DealSummary> {
  return apiRequest<DealSummary>(`/api/v2/workspaces/${ws()}/deals/${dealId}`);
}

export async function recordPurchase(input: {
  listingId: string;
  amountMinor: number;
  idempotencyKey: string;
}): Promise<unknown> {
  return apiRequest(`/api/v2/workspaces/${ws()}/deals`, {
    method: 'POST',
    headers: { 'Idempotency-Key': input.idempotencyKey },
    body: JSON.stringify({
      listing_id: input.listingId,
      amount_minor: input.amountMinor,
    }),
  });
}

export async function recordCost(input: {
  dealId: string;
  kind: string;
  amountMinor: number;
  idempotencyKey: string;
}): Promise<unknown> {
  return apiRequest(
    `/api/v2/workspaces/${ws()}/deals/${input.dealId}/costs`,
    {
      method: 'POST',
      headers: { 'Idempotency-Key': input.idempotencyKey },
      body: JSON.stringify({
        kind: input.kind,
        amount_minor: input.amountMinor,
      }),
    },
  );
}

export async function recordSale(input: {
  dealId: string;
  amountMinor: number;
  idempotencyKey: string;
}): Promise<unknown> {
  return apiRequest(`/api/v2/workspaces/${ws()}/deals/${input.dealId}/sell`, {
    method: 'POST',
    headers: { 'Idempotency-Key': input.idempotencyKey },
    body: JSON.stringify({ amount_minor: input.amountMinor }),
  });
}
