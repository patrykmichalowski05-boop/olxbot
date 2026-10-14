import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';
import { useColorScheme } from 'react-native';

import AsyncStorage from '@react-native-async-storage/async-storage';

import {
  darkColors,
  lightColors,
  radii,
  spacing,
  ThemeColors,
  typography,
} from './tokens';

export type ThemePreference = 'system' | 'dark' | 'light';

type ThemeContextValue = {
  colors: ThemeColors;
  spacing: typeof spacing;
  radii: typeof radii;
  typography: typeof typography;
  preference: ThemePreference;
  setPreference: (value: ThemePreference) => void;
  isDark: boolean;
};

const STORAGE_KEY = 'flipradar_theme_pref';

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const system = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('system');

  React.useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((value) => {
        if (value === 'dark' || value === 'light' || value === 'system') {
          setPreferenceState(value);
        }
      })
      .catch(() => undefined);
  }, []);

  const setPreference = useCallback((value: ThemePreference) => {
    setPreferenceState(value);
    AsyncStorage.setItem(STORAGE_KEY, value).catch(() => undefined);
  }, []);

  const isDark =
    preference === 'system' ? system !== 'light' : preference === 'dark';

  const colors = isDark ? darkColors : lightColors;

  const value = useMemo(
    () => ({
      colors,
      spacing,
      radii,
      typography,
      preference,
      setPreference,
      isDark,
    }),
    [colors, preference, setPreference, isDark],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return ctx;
}
