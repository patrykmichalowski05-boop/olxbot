import { apiRequest } from "@/api/client";
import { clearTokens, saveTokens } from "@/api/session";
import type { AuthTokens, MeResponse } from "@/api/types/auth";
import { portalEnabled } from "@/utils/config";

export async function login(username: string, password: string): Promise<void> {
  const path = portalEnabled()
    ? "/api/v1/portal/auth/login"
    : "/api/v1/auth/login";
  const tokens = await apiRequest<AuthTokens>(path, {
    method: "POST",
    body: JSON.stringify({ username, password }),
    auth: false,
  });
  await saveTokens(tokens);
}

export async function logout(): Promise<void> {
  if (portalEnabled()) {
    await apiRequest("/api/v1/portal/auth/logout", {
      method: "POST",
      auth: true,
    });
    await clearTokens();
    return;
  }
  try {
    await apiRequest<{ ok: boolean }>("/api/v1/auth/logout", {
      method: "POST",
    });
  } catch {
    // lokalne wylogowanie ma działać zawsze
  } finally {
    await clearTokens();
  }
}

export async function register(
  username: string,
  email: string,
  password: string,
): Promise<void> {
  const tokens = await apiRequest<AuthTokens>("/api/v1/portal/auth/register", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ username, email, password }),
  });
  await saveTokens(tokens);
}

export async function fetchMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>("/api/v1/me");
}
