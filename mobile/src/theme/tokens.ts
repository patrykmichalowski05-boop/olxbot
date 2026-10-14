import { Platform } from 'react-native';

export type ColorSchemeName = 'dark' | 'light';

export type ThemeColors = {
  background: string;
  surface: string;
  surfaceElevated: string;
  sidebar: string;
  border: string;
  text: string;
  textMuted: string;
  accent: string;
  accentMuted: string;
  success: string;
  successBg: string;
  risk: string;
  riskBg: string;
  loss: string;
  lossBg: string;
  warning: string;
  overlay: string;
};

export const darkColors: ThemeColors = {
  background: '#0B1120',
  surface: '#172033',
  surfaceElevated: '#1C2940',
  sidebar: '#0F172A',
  border: '#263449',
  text: '#F1F5F9',
  textMuted: '#94A3B8',
  accent: '#14B8A6',
  accentMuted: '#123A3B',
  success: '#22C55E',
  successBg: '#0F2A22',
  risk: '#F59E0B',
  riskBg: '#2A220F',
  loss: '#EF4444',
  lossBg: '#2A1414',
  warning: '#F59E0B',
  overlay: 'rgba(11, 18, 32, 0.72)',
};

export const lightColors: ThemeColors = {
  background: '#F8FAFC',
  surface: '#FFFFFF',
  surfaceElevated: '#F1F5F9',
  sidebar: '#FFFFFF',
  border: '#CBD5E1',
  text: '#0F172A',
  textMuted: '#64748B',
  accent: '#0D9488',
  accentMuted: '#CCFBF1',
  success: '#059669',
  successBg: '#ECFDF5',
  risk: '#D97706',
  riskBg: '#FFFBEB',
  loss: '#DC2626',
  lossBg: '#FEF2F2',
  warning: '#EA580C',
  overlay: 'rgba(15, 23, 42, 0.5)',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
} as const;

const fontFamily = Platform.OS === 'web' ? 'system-ui' : 'System';

export const typography = {
  title: { fontFamily, fontSize: 28, fontWeight: '700' as const, lineHeight: 36 },
  headline: { fontFamily, fontSize: 18, fontWeight: '600' as const, lineHeight: 24 },
  body: { fontFamily, fontSize: 15, fontWeight: '400' as const, lineHeight: 21 },
  bodyStrong: { fontFamily, fontSize: 15, fontWeight: '600' as const, lineHeight: 21 },
  caption: { fontFamily, fontSize: 12, fontWeight: '400' as const, lineHeight: 16 },
  money: { fontFamily, fontSize: 22, fontWeight: '700' as const, lineHeight: 28 },
  moneySmall: { fontFamily, fontSize: 16, fontWeight: '700' as const, lineHeight: 22 },
};

export const touchTarget = 48;
