import { apiRequest } from '@/api/client';
import { clearTokens, saveTokens } from '@/api/session';
import type { AuthTokens, MeResponse } from '@/api/types/auth';

export async function login(username: string, password: string): Promise<void> {
  const tokens = await apiRequest<AuthTokens>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    auth: false,
  });
  await saveTokens(tokens);
}

export async function logout(): Promise<void> {
  try {
    await apiRequest<{ ok: boolean }>('/api/v1/auth/logout', {
      method: 'POST',
    });
  } catch {
    // lokalne wylogowanie ma działać zawsze
  } finally {
    await clearTokens();
  }
}

export async function fetchMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>('/api/v1/me');
}
