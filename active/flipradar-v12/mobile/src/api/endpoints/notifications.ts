import { apiRequest } from '@/api/client';
import { mapInboxEvent, type InboxEvent, type NotificationsPage } from '@/api/mappers/notification';

export async function fetchNotificationsPage(
  workspaceId: string,
  beforeId: string | null = null,
): Promise<NotificationsPage> {
  if (!workspaceId.trim()) throw new Error('Brak EXPO_PUBLIC_FLIP_WORKSPACE_ID');
  const params = new URLSearchParams({ limit: '30' });
  if (beforeId) params.set('before_id', beforeId);
  const page = await apiRequest<{
    items: InboxEvent[];
    next_before_id: string | null;
  }>(`/api/v2/workspaces/${encodeURIComponent(workspaceId)}/notifications?${params}`);
  return {
    items: page.items.map(mapInboxEvent),
    nextBeforeId: page.next_before_id ?? null,
  };
}
