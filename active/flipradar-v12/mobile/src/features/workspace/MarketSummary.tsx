import React from "react";
import { Text, View } from "react-native";
import type { OpportunityCard } from "@/features/opportunity/types";
import { useTheme } from "@/theme/ThemeProvider";
import { formatUserDateTime } from "@/utils/datetime";
import { useWorkspaceLayout } from "./layout";
import { loadedPriceSummary, priceLabel } from "./presentation";

export function MetricTile({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  const { colors, typography, radii } = useTheme();
  return (
    <View
      style={{
        borderWidth: 1,
        borderColor: colors.border,
        backgroundColor: colors.surface,
        borderRadius: radii.md,
        padding: 12,
        gap: 4,
        flex: 1,
        minWidth: 0,
      }}
    >
      <Text
        style={[
          typography.caption,
          {
            color: colors.textMuted,
            letterSpacing: 0.45,
            textTransform: "uppercase",
          },
        ]}
      >
        {label}
      </Text>
      <Text
        style={[
          typography.bodyStrong,
          {
            fontSize: 18,
            lineHeight: 24,
            color: accent ?? colors.text,
            fontVariant: ["tabular-nums"],
          },
        ]}
      >
        {value}
      </Text>
    </View>
  );
}

export function MarketSummary({
  items,
  title = "Analiza cen",
  periodDays,
  scanAt,
  loading,
}: {
  items: OpportunityCard[];
  title?: string;
  periodDays?: number | null;
  scanAt?: string | null;
  loading?: boolean;
}) {
  const { colors, radii, typography } = useTheme();
  const { narrow, contentWidth } = useWorkspaceLayout();
  const summary = loadedPriceSummary(items);
  const range = (low: number | null, high: number | null) =>
    low === null || high === null
      ? "—"
      : `${priceLabel(low).replace(" zł", "")}–${priceLabel(high)}`;
  const metrics = [
    ["Ofert wczytanych", String(summary.count)],
    ["Mediana ofert", priceLabel(summary.medianMinor)],
    ["Typowy zakres", range(summary.lowMinor, summary.highMinor)],
    ["Min–max", range(summary.minMinor, summary.maxMinor)],
    ["Okres porównań", periodDays ? `${periodDays} dni` : "—"],
    [
      scanAt ? "Ostatni skan" : "Ostatnia obserwacja",
      formatUserDateTime(scanAt ?? summary.latestAt),
    ],
  ];
  return (
    <View
      style={{
        backgroundColor: colors.navigation,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radii.xl,
        padding: narrow ? 24 : 20,
        gap: 14,
      }}
    >
      <View
        style={{
          flexDirection: narrow ? "column" : "row",
          justifyContent: "space-between",
          gap: 10,
        }}
      >
        <Text style={[typography.headline, { color: colors.text }]}>
          {title}
        </Text>
        <Text style={[typography.caption, { color: colors.textMuted }]}>
          {scanAt ? "Ostatni skan" : "Ostatnia obserwacja"}:{" "}
          {formatUserDateTime(scanAt ?? summary.latestAt)}
        </Text>
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        {metrics.map(([label, value]) => (
          <View
            key={label}
            style={{
              flexGrow: 1,
              flexBasis: narrow ? "46%" : contentWidth < 1150 ? "30%" : "14%",
              minWidth: 0,
            }}
          >
            <MetricTile label={label} value={loading ? "—" : value} />
          </View>
        ))}
      </View>
      <Text style={[typography.caption, { color: colors.textMuted }]}>
        Statystyki wczytanych ofert. Typowy zakres obejmuje środkową połowę cen;
        nie jest wyceną konkretnego wariantu.
      </Text>
    </View>
  );
}
