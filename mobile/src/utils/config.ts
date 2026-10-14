import { Platform } from 'react-native';

export type AppMode = 'live' | 'demo';

export function apiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_FLIP_API_URL ?? '').replace(/\/$/, '');
}

export function radarSource(): 'legacy' | 'universal' {
  return process.env.EXPO_PUBLIC_FLIP_RADAR_SOURCE === 'universal'
    ? 'universal'
    : 'legacy';
}

export function workspaceId(): string | null {
  const id = process.env.EXPO_PUBLIC_FLIP_WORKSPACE_ID?.trim();
  return id || null;
}

export function isHttpsApiConfigured(): boolean {
  const base = apiBaseUrl();
  if (!base) {
    return false;
  }
  if (base.startsWith('https://')) {
    return true;
  }
  if (__DEV__ && process.env.EXPO_PUBLIC_FLIP_ALLOW_HTTP === '1') {
    return base.startsWith('http://');
  }
  return false;
}

export function resolveAppMode(): AppMode {
  if (process.env.EXPO_PUBLIC_FLIP_APP_MODE === 'demo') {
    return 'demo';
  }
  if (process.env.EXPO_PUBLIC_FLIP_APP_MODE === 'live') {
    return 'live';
  }
  if (!isHttpsApiConfigured()) {
    return 'demo';
  }
  if (Platform.OS === 'web' && process.env.EXPO_PUBLIC_FLIP_WEB_LIVE !== '1') {
    return 'demo';
  }
  return 'live';
}
