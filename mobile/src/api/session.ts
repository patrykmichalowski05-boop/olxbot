import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const ACCESS = 'flip_access';
const REFRESH = 'flip_refresh';
const RETURN_PATH = 'flip_return_path';

type Tokens = {
  access_token: string;
  refresh_token: string;
};

const memory: Partial<Tokens & { returnPath: string }> = {};

function secureStoreAvailable(): boolean {
  return Platform.OS !== 'web';
}

export async function saveTokens(tokens: Tokens): Promise<void> {
  if (secureStoreAvailable()) {
    await SecureStore.setItemAsync(ACCESS, tokens.access_token);
    await SecureStore.setItemAsync(REFRESH, tokens.refresh_token);
    return;
  }
  memory.access_token = tokens.access_token;
  memory.refresh_token = tokens.refresh_token;
}

export async function readAccessToken(): Promise<string | null> {
  if (secureStoreAvailable()) {
    return SecureStore.getItemAsync(ACCESS);
  }
  return memory.access_token ?? null;
}

export async function readRefreshToken(): Promise<string | null> {
  if (secureStoreAvailable()) {
    return SecureStore.getItemAsync(REFRESH);
  }
  return memory.refresh_token ?? null;
}

export async function clearTokens(): Promise<void> {
  if (secureStoreAvailable()) {
    await SecureStore.deleteItemAsync(ACCESS);
    await SecureStore.deleteItemAsync(REFRESH);
    return;
  }
  delete memory.access_token;
  delete memory.refresh_token;
}

export async function hasSession(): Promise<boolean> {
  return Boolean(await readAccessToken());
}

export async function saveReturnPath(path: string): Promise<void> {
  if (secureStoreAvailable()) {
    await SecureStore.setItemAsync(RETURN_PATH, path);
    return;
  }
  memory.returnPath = path;
}

export async function consumeReturnPath(): Promise<string | null> {
  if (secureStoreAvailable()) {
    const value = await SecureStore.getItemAsync(RETURN_PATH);
    if (value) {
      await SecureStore.deleteItemAsync(RETURN_PATH);
    }
    return value;
  }
  const value = memory.returnPath ?? null;
  delete memory.returnPath;
  return value;
}
