import { apiRequest } from "@/api/client";
import { readAccessToken } from "@/api/session";
import type {
  Account,
  AdminData,
  PlanCode,
  PriceResult,
  PublicConfig,
} from "@/features/portal/types";
import type { NotificationsPage } from "@/api/mappers/notification";

export function operationId(): string {
  return typeof globalThis.crypto?.randomUUID === "function"
    ? globalThis.crypto.randomUUID()
    : `op-${Date.now()}-${Math.random().toString(36).slice(2, 15)}`;
}
export function getAccount(signal?: AbortSignal) {
  return apiRequest<Account>("/api/v1/portal/me", { signal });
}
export function getPublicConfig() {
  return apiRequest<PublicConfig>("/api/v1/public/config", { auth: false });
}
export async function publicPriceSearch(
  query: string,
  operation: string,
): Promise<PriceResult> {
  return apiRequest("/api/v1/public/search", {
    method: "POST",
    auth: Boolean(await readAccessToken()),
    body: JSON.stringify({ query, operation }),
  });
}
export function requestPlan(plan: PlanCode) {
  return apiRequest("/api/v1/portal/plan-requests", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}
export function getAdminData(signal?: AbortSignal) {
  return apiRequest<AdminData>("/api/v1/portal/admin", { signal });
}
export function updateMemberAccess(
  userId: string,
  action: "activate" | "disable",
  plan?: PlanCode,
  operation = operationId(),
) {
  return apiRequest("/api/v1/portal/admin/access", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, action, plan, operation }),
  });
}
export async function getPortalNotifications(
  beforeId: string | null,
): Promise<NotificationsPage> {
  const params = new URLSearchParams();
  if (beforeId) params.set("before_id", beforeId);
  const result = await apiRequest<{
    items: NotificationsPage["items"];
    next_before_id: string | null;
  }>(`/api/v1/portal/notifications?${params}`);
  return { items: result.items, nextBeforeId: result.next_before_id };
}

/** Deletes a V10 account and its own private data. Owner/admin only. */
export function deleteMemberAccount(userId: string, confirm: string) {
  return apiRequest<{ok: boolean}>("/api/v1/portal/admin/delete", {
    method: "POST", body: JSON.stringify({ user_id: userId, confirm }),
  });
}
