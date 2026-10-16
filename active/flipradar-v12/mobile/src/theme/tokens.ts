export type ColorSchemeName = "dark" | "light";

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
  primary: string;
  onPrimary: string;
  navigation: string;
  focus: string;
};

export const darkColors: ThemeColors = {
  background: "#080F1C",
  surface: "#101B2C",
  surfaceElevated: "#17253A",
  border: "#223249",
  text: "#F2F6FC",
  textMuted: "#9AADC5",
  textSubtle: "#8196B1",
  accent: "#40DCE5",
  accentMuted: "#218C99",
  accentBg: "#11303D",
  onAccent: "#071A24",
  success: "#59DCA5",
  successBg: "#12302A",
  risk: "#F0BC61",
  riskBg: "#332A1B",
  loss: "#F88791",
  lossBg: "#341E2A",
  warning: "#F0BC61",
  warningBg: "#332A1B",
  overlay: "rgba(3, 8, 18, 0.78)",
  primary: "#66C4FF",
  onPrimary: "#142D3F",
  navigation: "#0D1827",
  focus: "#66C4FF",
};

export const lightColors: ThemeColors = {
  background: "#FFFFFF",
  surface: "#FFFFFF",
  surfaceElevated: "#EDF3F7",
  border: "#D2E0EB",
  text: "#172D40",
  textMuted: "#4C6780",
  accent: "#075B6D",
  accentMuted: "#8CD7E3",
  success: "#18753E",
  successBg: "#E4F5EB",
  risk: "#8C5300",
  riskBg: "#FFF3DF",
  loss: "#B23C46",
  lossBg: "#FDECEF",
  warning: "#8C5300",
  overlay: "rgba(18, 39, 56, 0.35)",
  accentBg: "#DDFBFF",
  onAccent: "#FFFFFF",
  textSubtle: "#5C7487",
  warningBg: "#FFF3DF",
  primary: "#66C4FF",
  onPrimary: "#102D42",
  navigation: "#F4F9FC",
  focus: "#218BC9",
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
  md: 10,
  lg: 12,
  xl: 16,
  xxl: 16,
  pill: 999,
} as const;

export const typography = {
  label: {
    fontSize: 11,
    fontWeight: "700" as const,
    lineHeight: 16,
    letterSpacing: 1.1,
  },
  tab: { fontSize: 11, fontWeight: "600" as const, lineHeight: 16 },
  hero: {
    fontSize: 36,
    fontWeight: "700" as const,
    lineHeight: 44,
    letterSpacing: -1.2,
  },
  title: {
    fontSize: 24,
    fontWeight: "700" as const,
    lineHeight: 32,
    letterSpacing: -0.45,
  },
  headline: { fontSize: 18, fontWeight: "600" as const, lineHeight: 24 },
  body: { fontSize: 14, fontWeight: "400" as const, lineHeight: 21 },
  bodyStrong: { fontSize: 14, fontWeight: "600" as const, lineHeight: 21 },
  caption: { fontSize: 12, fontWeight: "400" as const, lineHeight: 16 },
  money: { fontSize: 22, fontWeight: "700" as const, lineHeight: 28 },
  moneySmall: { fontSize: 16, fontWeight: "700" as const, lineHeight: 22 },
};

export const touchTarget = 44;
export const layout = {
  contentMaxWidth: 1440,
  formMaxWidth: 800,
  sidebarWidth: 248,
  sidebarBreakpoint: 1100,
  desktopPadding: 32,
  mobilePadding: 20,
} as const;
