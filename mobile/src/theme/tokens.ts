export type ColorSchemeName = 'dark' | 'light';

export type ThemeColors = {
  background: string;
  surface: string;
  surfaceElevated: string;
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
  background: '#0B1220',
  surface: '#111C2E',
  surfaceElevated: '#162338',
  border: '#243047',
  text: '#F1F5F9',
  textMuted: '#A8B5C8',
  accent: '#2DD4BF',
  accentMuted: '#1A9E8C',
  success: '#34D399',
  successBg: '#0F2A22',
  risk: '#FBBF24',
  riskBg: '#2A220F',
  loss: '#F87171',
  lossBg: '#2A1414',
  warning: '#FB923C',
  overlay: 'rgba(11, 18, 32, 0.72)',
};

export const lightColors: ThemeColors = {
  background: '#F8FAFC',
  surface: '#FFFFFF',
  surfaceElevated: '#F1F5F9',
  border: '#CBD5E1',
  text: '#0F172A',
  textMuted: '#64748B',
  accent: '#0D9488',
  accentMuted: '#14B8A6',
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

export const typography = {
  title: { fontSize: 24, fontWeight: '700' as const, lineHeight: 30 },
  headline: { fontSize: 18, fontWeight: '600' as const, lineHeight: 24 },
  body: { fontSize: 15, fontWeight: '400' as const, lineHeight: 21 },
  bodyStrong: { fontSize: 15, fontWeight: '600' as const, lineHeight: 21 },
  caption: { fontSize: 12, fontWeight: '400' as const, lineHeight: 16 },
  money: { fontSize: 22, fontWeight: '700' as const, lineHeight: 28 },
  moneySmall: { fontSize: 16, fontWeight: '700' as const, lineHeight: 22 },
};

export const touchTarget = 48;
