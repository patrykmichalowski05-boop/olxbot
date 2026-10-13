import * as SecureStore from 'expo-secure-store';

const BASE = (
  process.env.EXPO_PUBLIC_FLIP_API_URL || ''
).replace(/\/$/, '');

const ACCESS = 'flip_access';
const REFRESH = 'flip_refresh';

export type RadarItem = {
  snapshot_id: number;
  decision: string;
  valuation: Record<string, unknown>;
  observed_at: string | null;
  title: string | null;
  platform: string;
  price_minor: number | null;
  url: string | null;
};

type Tokens = {
  access_token: string;
  refresh_token: string;
};

function baseUrl(): string {
  if (!BASE || !BASE.startsWith('https://')) {
    throw new Error(
      'Ustaw EXPO_PUBLIC_FLIP_API_URL na HTTPS'
    );
  }

  return BASE;
}

async function request(
  path: string,
  options: RequestInit = {},
  token?: string,
) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(
    `${baseUrl()}${path}`,
    { ...options, headers },
  );

  if (!response.ok) {
    throw new Error(`API HTTP ${response.status}`);
  }

  return response.json();
}

async function save(tokens: Tokens) {
  await SecureStore.setItemAsync(
    ACCESS, tokens.access_token
  );
  await SecureStore.setItemAsync(
    REFRESH, tokens.refresh_token
  );
}

export async function login(
  username: string,
  password: string,
) {
  const tokens = await request(
    '/api/v1/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({
        username,
        password,
      }),
    },
  ) as Tokens;

  await save(tokens);
}

export async function getRadar(): Promise<RadarItem[]> {
  let access = await SecureStore.getItemAsync(ACCESS);

  if (!access) {
    throw new Error('Brak sesji');
  }

  try {
    const response = await request(
      '/api/v1/radar?limit=50',
      {},
      access,
    );

    return response.items;

  } catch (error) {
    if (
      !(error instanceof Error)
      || error.message !== 'API HTTP 401'
    ) {
      throw error;
    }

    const refresh = await SecureStore.getItemAsync(
      REFRESH
    );

    if (!refresh) {
      throw error;
    }

    try {
      const tokens = await request(
        '/api/v1/auth/refresh',
        {
          method: 'POST',
          body: JSON.stringify({
            refresh_token: refresh,
          }),
        },
      ) as Tokens;

      await save(tokens);

      const response = await request(
        '/api/v1/radar?limit=50',
        {},
        tokens.access_token,
      );

      return response.items;

    } catch (refreshError) {
      await clearSession();
      throw refreshError;
    }
  }
}

export async function clearSession() {
  const token = await SecureStore.getItemAsync(
    ACCESS
  );

  if (token) {
    try {
      await request(
        '/api/v1/auth/logout',
        { method: 'POST' },
        token,
      );
    } catch {
      // Wylogowanie lokalne nadal musi dzialac.
    }
  }

  await SecureStore.deleteItemAsync(ACCESS);
  await SecureStore.deleteItemAsync(REFRESH);
}

export async function hasSession() {
  return Boolean(
    await SecureStore.getItemAsync(ACCESS)
  );
}
