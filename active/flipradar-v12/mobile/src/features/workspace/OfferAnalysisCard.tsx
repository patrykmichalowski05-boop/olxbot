import React, { useState } from "react";
import { Linking, Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Badge } from "@/components/Badge";
import { IconButton } from "@/components/IconButton";
import { PrimaryButton } from "@/components/PrimaryButton";
import { DecisionBadge } from "@/components/DecisionBadge";
import type { OpportunityCard } from "@/features/opportunity/types";
import {
  opportunityInsight,
  opportunityRisk,
} from "@/features/opportunity/presentation";
import { useTheme } from "@/theme/ThemeProvider";
import { formatUserDateTime } from "@/utils/datetime";
import { formatRoiBps } from "@/utils/money";
import { useWorkspaceLayout } from "./layout";
import { MetricTile } from "./MarketSummary";
import {
  checkedRecently,
  hasUsableComparison,
  confidenceLabel,
  platformName,
  priceAssessment,
  priceAssessmentText,
  priceLabel,
  safeOfferUrl,
} from "./presentation";

export function OfferAnalysisCard({
  item,
  demo,
  defaultExpanded = false,
  onDetails,
  onWatch,
  watched,
  watchLoading,
  watchDisabled,
}: {
  item: OpportunityCard;
  demo?: boolean;
  defaultExpanded?: boolean;
  onDetails?: () => void;
  onWatch?: () => void;
  watched?: boolean;
  watchLoading?: boolean;
  watchDisabled?: boolean;
}) {
  const { colors, typography, radii } = useTheme();
  const { narrow, contentWidth } = useWorkspaceLayout();
  const compact = contentWidth < 420;
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [openError, setOpenError] = useState("");
  const assessment = priceAssessment(item);
  const insight = opportunityInsight(item);
  const risk = opportunityRisk(item);
  const hasComparison = hasUsableComparison(item);
  const url = demo ? null : safeOfferUrl(item.platform, item.url);
  const metrics = [
    {
      label: "Ocena ceny",
      value: priceAssessmentText(item),
      accent:
        assessment.tone === "warning"
          ? colors.warning
          : assessment.tone === "success"
            ? colors.success
            : undefined,
    },
    {
      label: "Typowa cena",
      value: hasComparison ? priceLabel(item.market?.medianMinor) : "—",
    },
    {
      label: "Porównano z",
      value:
        hasComparison && item.market?.sampleCount != null
          ? `${item.market.sampleCount} ofertami`
          : "—",
    },
    {
      label: "Wiarygodność oceny",
      value: hasComparison ? confidenceLabel(item.market?.confidence) : "—",
    },
  ];
  return (
    <View
      style={{
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radii.xl,
        backgroundColor: colors.surface,
        padding: narrow ? 24 : 20,
        gap: 16,
      }}
    >
      <View
        style={{
          flexDirection: narrow ? "column" : "row",
          alignItems: narrow ? "stretch" : "flex-start",
          gap: 16,
        }}
      >
        <View style={{ flex: 1, minWidth: 0, gap: 8 }}>
          <View
            style={{ flexDirection: "row", alignItems: "flex-start", gap: 12 }}
          >
            <Text
              style={[
                typography.headline,
                {
                  color: colors.text,
                  flex: 1,
                  fontSize: narrow ? 20 : 16,
                  lineHeight: narrow ? 29 : 24,
                  fontWeight: "700",
                },
              ]}
            >
              {item.title}
            </Text>
            {onWatch ? (
              <IconButton
                icon={watched ? "bookmark" : "bookmark-outline"}
                label={watched ? "Usuń z zapisanych" : "Zapisz ofertę"}
                active={watched}
                onPress={onWatch}
                loading={watchLoading}
                disabled={watchDisabled}
              />
            ) : null}
          </View>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
            {demo ? (
              <Badge label="Przykład" tone="accent" />
            ) : checkedRecently(item.verifiedAt) ? (
              <Badge label="Sprawdzona · ostatnie 24 h" tone="success" />
            ) : null}
            <Badge
              label={
                assessment.tone === "warning"
                  ? `${assessment.label} — sprawdź dokładnie`
                  : assessment.label
              }
              tone={assessment.tone}
              icon={assessment.tone === "warning" ? "warning" : undefined}
            />
          </View>
        </View>
        <View
          style={{
            flexDirection: compact ? "column" : "row",
            alignItems: compact ? "stretch" : "center",
            justifyContent: "space-between",
            gap: 16,
            marginVertical: narrow ? 6 : 0,
          }}
        >
          <Text
            style={[
              typography.money,
              {
                color: colors.text,
                fontSize: narrow ? 30 : 24,
                lineHeight: 38,
                fontVariant: ["tabular-nums"],
              },
            ]}
          >
            {priceLabel(item.purchaseMinor)}
          </Text>
          <PrimaryButton
            label={
              demo
                ? "Oferta przykładowa"
                : url
                  ? `Otwórz w ${platformName(item.platform)}`
                  : "Brak linku do oferty"
            }
            icon={url ? "arrow-up-right-box-outline" : undefined}
            disabled={!url}
            onPress={() => {
              if (url)
                void Linking.openURL(url).catch(() =>
                  setOpenError(
                    "Nie udało się otworzyć ogłoszenia. Spróbuj ponownie.",
                  ),
                );
            }}
          />
        </View>
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        {metrics.map((metric) => (
          <View
            key={metric.label}
            style={{
              flexBasis: narrow ? "46%" : "22%",
              flexGrow: 1,
              minWidth: 0,
            }}
          >
            <MetricTile {...metric} />
          </View>
        ))}
      </View>
      <Text style={[typography.caption, { color: colors.textMuted }]}>
        Ostatnia obserwacja: {formatUserDateTime(item.verifiedAt)}
      </Text>
      <View
        style={{
          borderTopWidth: 1,
          borderColor: colors.border,
          paddingTop: 12,
          gap: 12,
        }}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ expanded }}
          aria-expanded={expanded}
          onPress={() => setExpanded((value) => !value)}
          style={{
            minHeight: 44,
            flexDirection: "row",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Ionicons
            name={expanded ? "chevron-down" : "chevron-forward"}
            size={14}
            color={colors.textMuted}
          />
          <Text style={[typography.bodyStrong, { color: colors.textMuted }]}>
            Szczegóły i założenia
          </Text>
        </Pressable>
        {expanded ? (
          <View style={{ gap: 14 }}>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
              <DecisionBadge decision={item.decision} />
              <Badge
                label={`ROI: ${item.hasValuation ? formatRoiBps(item.roiBps) : "—"}`}
                tone="accent"
              />
              <Badge label={platformName(item.platform)} />
              <Badge
                label={risk.label}
                tone={risk.tone}
                icon="shield-half-outline"
              />
            </View>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
              {[
                [
                  "Prognoza odsprzedaży",
                  item.hasValuation
                    ? priceLabel(item.resaleRange?.highMinor)
                    : "—",
                ],
                [
                  "Wynik po kosztach",
                  item.hasValuation
                    ? priceLabel(item.operatingProfitMinor)
                    : "—",
                ],
              ].map(([label, value]) => (
                <View
                  key={label}
                  style={{ flexBasis: narrow ? "100%" : "45%", flexGrow: 1 }}
                >
                  <MetricTile label={label} value={value} />
                </View>
              ))}
            </View>
            <Text style={[typography.body, { color: colors.textMuted }]}>
              <Text style={{ fontWeight: "700" }}>{insight.label}: </Text>
              {insight.text}
            </Text>
            {item.topRisk ? (
              <Text style={[typography.body, { color: colors.textMuted }]}>
                • {item.topRisk}
              </Text>
            ) : null}
            {item.market?.kind === "ASKING" ? (
              <Text style={[typography.body, { color: colors.textMuted }]}>
                • Porównanie obejmuje ceny ogłoszeń, a nie potwierdzone ceny
                sprzedaży.
              </Text>
            ) : null}
            <Text style={[typography.body, { color: colors.textMuted }]}>
              • Wynik jest prognozą przed podatkiem. Stan, wersja i koszty
              przedmiotu wymagają sprawdzenia przed zakupem.
            </Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
              {onDetails ? (
                <PrimaryButton
                  label="Pełne szczegóły"
                  variant="secondary"
                  onPress={onDetails}
                />
              ) : null}
            </View>
          </View>
        ) : null}
      </View>
      {openError ? (
        <Text
          accessibilityLiveRegion="polite"
          style={[typography.caption, { color: colors.loss }]}
        >
          {openError}
        </Text>
      ) : null}
    </View>
  );
}
