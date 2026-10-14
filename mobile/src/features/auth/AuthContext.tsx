import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { api, getAppMode } from '@/api';
import { checkApiReachable } from '@/api/client';
import { hasSession, saveTokens, clearTokens , saveReturnPath, consumeReturnPath } from '@/api/session';
import { usePathname, useRouter, useSegments } from 'expo-router';

type AuthState = {
  ready: boolean;
  signedIn: boolean;
  mode: ReturnType<typeof getAppMode>;
  userId: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkConnection: () => Promise<string>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const segments = useSegments();
  const pathname = usePathname();
  const mode = getAppMode();

  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      if (mode === 'demo') {
        const yes = await hasSession();
        if (alive) {
          setSignedIn(yes);
          setUserId(yes ? 'demo-user' : null);
          setReady(true);
        }
        return;
      }
      const yes = await hasSession();
      if (!alive) return;
      if (yes) {
        try {
          const me = await api.me();
          setUserId(me.user_id);
          setSignedIn(true);
        } catch {
          await clearTokens();
          setSignedIn(false);
        }
      }
      setReady(true);
    })();
    return () => {
      alive = false;
    };
  }, [mode]);

  useEffect(() => {
    if (!ready) return;
    const inAuth = segments[0] === '(auth)';
    if (!signedIn && !inAuth) {
      if (pathname !== '/login') {
        void saveReturnPath(pathname);
      }
      router.replace('/login');
      return;
    }
    if (signedIn && inAuth) {
      void (async () => {
        const dest = (await consumeReturnPath()) ?? '/dashboard';
        router.replace(dest as never);
      })();
    }
  }, [ready, signedIn, segments, pathname, router]);

  const login = useCallback(
    async (username: string, password: string) => {
      if (!username.trim() || !password) {
        throw new Error('Podaj login i hasło');
      }
      if (mode === 'demo') {
        await saveTokens({
          access_token: 'demo-access',
          refresh_token: 'demo-refresh-not-for-api',
        });
        setSignedIn(true);
        setUserId('demo-user');
        return;
      }
      await api.login(username.trim(), password);
      const me = await api.me();
      setUserId(me.user_id);
      setSignedIn(true);
    },
    [mode],
  );

  const logout = useCallback(async () => {
    await api.logout();
    await queryClient.clear();
    setSignedIn(false);
    setUserId(null);
    router.replace('/login');
  }, [queryClient, router]);

  const checkConnection = useCallback(async () => {
    if (mode === 'demo') {
      return 'Tryb DEMO — bez połączenia z API produkcyjnym.';
    }
    return checkApiReachable();
  }, [mode]);

  const value = useMemo(
    () => ({
      ready,
      signedIn,
      mode,
      userId,
      login,
      logout,
      checkConnection,
    }),
    [ready, signedIn, mode, userId, login, logout, checkConnection],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
