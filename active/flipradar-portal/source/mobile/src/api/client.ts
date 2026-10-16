import { Platform } from "react-native";
import {
  apiBaseUrl,
  isHttpsApiConfigured,
  portalEnabled,
} from "@/utils/config";
import { ApiError } from "@/api/errors";
import {
  clearTokens,
  readAccessToken,
  readRefreshToken,
  saveTokens,
} from "@/api/session";
import type { AuthTokens } from "@/api/types/auth";

let refreshPromise: Promise<string | null> | null = null;

function ensureBaseUrl(): string {
  const base = apiBaseUrl();
  if (!isHttpsApiConfigured()) {
    throw new ApiError(0, "Brak skonfigurowanego API (HTTPS).");
  }
  return base;
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    if (portalEnabled() && Platform.OS === "web") {
      const response = await fetch(
        `${ensureBaseUrl()}/api/v1/portal/auth/resume`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "X-FlipRadar-Client": "portal",
            Accept: "application/json",
          },
        },
      );
      if (!response.ok) {
        await clearTokens();
        return null;
      }
      const tokens = (await response.json()) as AuthTokens;
      await saveTokens(tokens);
      return tokens.access_token;
    }
    const refresh = await readRefreshToken();
    if (!refresh) {
      await clearTokens();
      return null;
    }

    const response = await fetch(`${ensureBaseUrl()}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });

    if (!response.ok) {
      await clearTokens();
      return null;
    }

    const tokens = (await response.json()) as AuthTokens;
    await saveTokens(tokens);
    return tokens.access_token;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

export async function restoreBrowserSession(): Promise<boolean> {
  return portalEnabled() && Platform.OS === "web"
    ? Boolean(await refreshAccessToken())
    : false;
}

export type ApiRequestOptions = RequestInit & {
  auth?: boolean;
  retry401?: boolean;
};

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { auth = true, retry401 = true, ...init } = options;
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(portalEnabled() ? { "X-FlipRadar-Client": "portal" } : {}),
    ...(init.body ? { "Content-Type": "application/json" } : {}),
    ...(init.headers as Record<string, string> | undefined),
  };

  if (auth) {
    const access = await readAccessToken();
    if (!access) {
      throw new ApiError(401, "Brak sesji");
    }
    headers.Authorization = `Bearer ${access}`;
  }

  const response = await fetch(`${ensureBaseUrl()}${path}`, {
    ...(portalEnabled() && Platform.OS === "web"
      ? { credentials: "include" as const }
      : {}),
    ...init,
    headers,
  });

  if (response.status === 401 && auth && retry401) {
    const next = await refreshAccessToken();
    if (!next) {
      throw new ApiError(401, "Sesja wygasła");
    }
    return apiRequest<T>(path, { ...options, retry401: false });
  }

  const text = await response.text();
  let body: unknown = undefined;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, `API HTTP ${response.status}`, body);
  }

  return body as T;
}

export async function checkApiReachable(): Promise<string> {
  const base = ensureBaseUrl();
  const response = await fetch(`${base}/api/v1/me`, {
    headers: { Accept: "application/json" },
  });

  if (response.status !== 401) {
    throw new ApiError(
      response.status,
      `Nieoczekiwany status: ${response.status}`,
    );
  }

  const body = await response.json();
  if (body?.detail !== "Unauthorized") {
    throw new Error("Serwer nie wygląda na Flip Hunter API");
  }

  return "Połączenie z API działa.";
}
