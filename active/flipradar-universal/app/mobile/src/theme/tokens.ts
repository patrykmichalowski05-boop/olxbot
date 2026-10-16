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
  accentBg: string;
  onAccent: string;
  textSubtle: string;
  warningBg: string;
};

export const darkColors: ThemeColors = {
  background: '#080F1C',
  surface: '#101B2C',
  surfaceElevated: '#17253A',
  border: '#223249',
  text: '#F2F6FC',
  textMuted: '#9AADC5',
  textSubtle: '#8196B1',
  accent: '#40DCE5',
  accentMuted: '#218C99',
  accentBg: '#11303D',
  onAccent: '#071A24',
  success: '#59DCA5',
  successBg: '#12302A',
  risk: '#F0BC61',
  riskBg: '#332A1B',
  loss: '#F88791',
  lossBg: '#341E2A',
  warning: '#F0BC61',
  warningBg: '#332A1B',
  overlay: 'rgba(3, 8, 18, 0.78)',
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
  accentBg: '#E1F5F6',
  onAccent: '#FFFFFF',
  textSubtle: '#64748B',
  warningBg: '#FFFBEB',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  section: 20,
  xl: 24,
  xxl: 32,
} as const;

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  pill: 999,
} as const;

export const typography = {
  label: { fontSize: 11, fontWeight: '700' as const, lineHeight: 16, letterSpacing: 1.1 },
  tab: { fontSize: 11, fontWeight: '600' as const, lineHeight: 16 },
  hero: { fontSize: 36, fontWeight: '700' as const, lineHeight: 44, letterSpacing: -1.2 },
  title: {
    fontSize: 28,
    fontWeight: '700' as const,
    lineHeight: 34,
    letterSpacing: -0.8,
  },
  headline: { fontSize: 18, fontWeight: '600' as const, lineHeight: 24 },
  body: { fontSize: 15, fontWeight: '400' as const, lineHeight: 21 },
  bodyStrong: { fontSize: 15, fontWeight: '600' as const, lineHeight: 21 },
  caption: { fontSize: 12, fontWeight: '400' as const, lineHeight: 16 },
  money: { fontSize: 22, fontWeight: '700' as const, lineHeight: 28 },
  moneySmall: { fontSize: 16, fontWeight: '700' as const, lineHeight: 22 },
};

export const touchTarget = 44;
export const layout = { contentMaxWidth: 1040, formMaxWidth: 640 } as const;
