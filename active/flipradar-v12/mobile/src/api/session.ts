import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import { safeReturnPath } from "@/features/portal/navigation";

const ACCESS = "flip_access";
const REFRESH = "flip_refresh";
const RETURN_PATH = "flip_return_path";

type Tokens = {
  access_token: string;
  refresh_token: string;
};

const memory: Partial<Tokens & { returnPath: string }> = {};

function shouldUseSecureStore(): boolean {
  return Platform.OS !== "web";
}

export async function saveTokens(tokens: Tokens): Promise<void> {
  if (shouldUseSecureStore()) {
    await SecureStore.setItemAsync(ACCESS, tokens.access_token);
    await SecureStore.setItemAsync(REFRESH, tokens.refresh_token);
    return;
  }
  memory.access_token = tokens.access_token;
  memory.refresh_token = tokens.refresh_token;
}

export async function readAccessToken(): Promise<string | null> {
  if (shouldUseSecureStore()) {
    return SecureStore.getItemAsync(ACCESS);
  }
  return memory.access_token ?? null;
}

export async function readRefreshToken(): Promise<string | null> {
  if (shouldUseSecureStore()) {
    return SecureStore.getItemAsync(REFRESH);
  }
  return memory.refresh_token ?? null;
}

export async function clearTokens(): Promise<void> {
  if (shouldUseSecureStore()) {
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
  const safe = safeReturnPath(path);
  if (!safe) return;
  if (shouldUseSecureStore()) {
    await SecureStore.setItemAsync(RETURN_PATH, safe);
    return;
  }
  memory.returnPath = safe;
  try {
    globalThis.sessionStorage?.setItem(RETURN_PATH, safe);
  } catch {
    /* optional tab storage */
  }
}

export async function consumeReturnPath(): Promise<string | null> {
  if (shouldUseSecureStore()) {
    const value = await SecureStore.getItemAsync(RETURN_PATH);
    if (value) {
      await SecureStore.deleteItemAsync(RETURN_PATH);
    }
    return safeReturnPath(value);
  }
  let value = memory.returnPath ?? null;
  try {
    value = value ?? globalThis.sessionStorage?.getItem(RETURN_PATH);
    globalThis.sessionStorage?.removeItem(RETURN_PATH);
  } catch {
    /* optional tab storage */
  }
  delete memory.returnPath;
  return safeReturnPath(value);
}
