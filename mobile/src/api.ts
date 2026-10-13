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

export type RadarPage = {
  items: RadarItem[];
  next_before_id: number | null;
};

export async function getRadarPage(
  beforeId: number | null = null,
  query: string = '',
): Promise<RadarPage> {
  const q = query.trim().slice(0, 120);
  const path = '/api/v1/radar?limit=50'
    + (beforeId !== null
      ? `&before_id=${beforeId}` : '')
    + (q ? `&q=${encodeURIComponent(q)}` : '');

  const access = await SecureStore.getItemAsync(ACCESS);

  if (!access) {
    throw new Error('Brak sesji');
  }

  try {
    return await request(path, {}, access) as RadarPage;
  } catch (error) {
    if (
      !(error instanceof Error)
      || error.message !== 'API HTTP 401'
    ) {
      throw error;
    }

    const refreshToken =
      await SecureStore.getItemAsync(REFRESH);

    if (!refreshToken) {
      await clearSession();
      throw error;
    }

    try {
      const tokens = await request(
        '/api/v1/auth/refresh',
        {
          method: 'POST',
          body: JSON.stringify({
            refresh_token: refreshToken,
          }),
        },
      ) as Tokens;

      await save(tokens);

      return await request(
        path, {}, tokens.access_token
      ) as RadarPage;
    } catch (refreshError) {
      await clearSession();
      throw refreshError;
    }
  }
}

export async function getRadar(): Promise<RadarItem[]> {
  return (await getRadarPage()).items;
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


export type FlipPreviewInput = {
  purchase_minor: number;
  sale_minor: number;
  costs: Record<string, number>;
  confidence: string;
  condition: string;
};

export type FlipPreviewResult = {
  purchase_minor: number;
  sale_minor: number;
  total_cost_minor: number;
  total_investment_minor: number;
  operating_profit_minor: number;
  roi_bps: number;
  max_purchase_minor: number;
  decision: string;
  policy_version: string;
  profit_after_tax: boolean;
};

export async function previewFlip(
  payload: FlipPreviewInput,
): Promise<FlipPreviewResult> {
  const path = '/api/v1/valuations/preview';

  const options: RequestInit = {
    method: 'POST',
    body: JSON.stringify(payload),
  };

  const access = await SecureStore.getItemAsync(ACCESS);

  if (!access) {
    throw new Error('Brak sesji. Zaloguj się ponownie.');
  }

  try {
    return await request(
      path,
      options,
      access,
    ) as FlipPreviewResult;
  } catch (error) {
    if (
      !(error instanceof Error) ||
      error.message !== 'API HTTP 401'
    ) {
      throw error;
    }
  }

  const refreshToken =
    await SecureStore.getItemAsync(REFRESH);

  if (!refreshToken) {
    await clearSession();
    throw new Error('Sesja wygasła.');
  }

  try {
    const tokens = await request(
      '/api/v1/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      },
    ) as Tokens;

    await save(tokens);

    return await request(
      path,
      options,
      tokens.access_token,
    ) as FlipPreviewResult;
  } catch (error) {
    await clearSession();
    throw error;
  }
}
