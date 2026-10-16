import React, { useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Badge } from "@/components/Badge";
import { IconButton, type IconName } from "@/components/IconButton";
import type { OpportunityCard } from "@/features/opportunity/types";
import { useTheme } from "@/theme/ThemeProvider";
import { useWorkspaceLayout } from "./layout";
import {
  offerTags,
  platformName,
  priceAssessment,
  priceLabel,
} from "./presentation";

export type OfferRowProps = {
  item: OpportunityCard;
  onPress: () => void;
  onWatch?: () => void;
  watched?: boolean;
  watchLoading?: boolean;
  watchDisabled?: boolean;
  last?: boolean;
};
export function OfferRow({
  item,
  onPress,
  onWatch,
  watched,
  watchLoading,
  watchDisabled,
  last,
}: OfferRowProps) {
  const { colors, typography, radii } = useTheme();
  const { narrow } = useWorkspaceLayout();
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const assessment = priceAssessment(item);
  const tags = offerTags(item);
  const icon: IconName =
    item.category === "CAR"
      ? "car-sport-outline"
      : item.category === "FASHION"
        ? "shirt-outline"
        : item.category === "ELECTRONICS"
          ? "desktop-outline"
          : "cube-outline";
  return (
    <View
      style={{
        backgroundColor: colors.surface,
        paddingVertical: 16,
        paddingHorizontal: narrow ? 16 : 20,
        borderBottomWidth: last ? 0 : 1,
        borderColor: colors.border,
        gap: 12,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: 16 }}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Szczegóły oferty: ${item.title}`}
          onPress={onPress}
          style={{
            flex: 1,
            minWidth: 0,
            flexDirection: "row",
            gap: 16,
            alignItems: "center",
          }}
        >
          <View
            style={{
              width: narrow ? 52 : 72,
              height: 56,
              backgroundColor: colors.accentBg,
              borderWidth: 1,
              borderColor: colors.border,
              borderRadius: radii.md,
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
            }}
          >
            {item.imageUrl && failedUrl !== item.imageUrl ? (
              <Image
                source={{ uri: item.imageUrl }}
                onError={() => setFailedUrl(item.imageUrl ?? null)}
                resizeMode="cover"
                style={{ width: "100%", height: "100%" }}
              />
            ) : (
              <Ionicons name={icon} size={25} color={colors.accent} />
            )}
          </View>
          <View style={{ flex: 1, minWidth: 0, gap: 6 }}>
            <Text
              numberOfLines={2}
              style={[
                typography.bodyStrong,
                { color: colors.text, fontSize: narrow ? 15 : 14 },
              ]}
            >
              {item.title}
            </Text>
            <View
              style={{
                flexDirection: "row",
                flexWrap: "wrap",
                alignItems: "center",
                gap: 5,
              }}
            >
              <Badge
                label={platformName(item.platform)}
                tone={item.platform === "FACEBOOK" ? "accent" : "neutral"}
              />
              {!narrow
                ? tags.map((tag) => (
                    <Text
                      key={tag}
                      style={[
                        typography.caption,
                        {
                          color: colors.textMuted,
                          backgroundColor: colors.surfaceElevated,
                          borderRadius: 5,
                          paddingHorizontal: 7,
                          paddingVertical: 3,
                        },
                      ]}
                    >
                      {tag}
                    </Text>
                  ))
                : null}
            </View>
            {!narrow && item.hasValuation ? (
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                Odsprzedaż: {priceLabel(item.resaleRange?.highMinor)} · wynik po
                kosztach: {priceLabel(item.operatingProfitMinor)}
              </Text>
            ) : null}
          </View>
        </Pressable>
        {!narrow ? (
          <View style={{ minWidth: 140, alignItems: "flex-end", gap: 7 }}>
            <Text
              style={[
                typography.money,
                { color: colors.text, fontVariant: ["tabular-nums"] },
              ]}
            >
              {priceLabel(item.purchaseMinor)}
            </Text>
            <Badge
              label={assessment.label}
              tone={assessment.tone}
              icon={
                assessment.tone === "warning"
                  ? "warning"
                  : assessment.tone === "success"
                    ? "checkmark"
                    : undefined
              }
            />
          </View>
        ) : null}
        {onWatch && !narrow ? (
          <IconButton
            icon={watched ? "bookmark" : "bookmark-outline"}
            label={watched ? "Usuń z zapisanych" : "Zapisz ofertę"}
            active={watched}
            loading={watchLoading}
            disabled={watchDisabled}
            onPress={onWatch}
          />
        ) : null}
      </View>
      {narrow ? (
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            gap: 8,
            justifyContent: "space-between",
          }}
        >
          <View style={{ gap: 6, flex: 1, minWidth: 0 }}>
            <Text style={[typography.money, { color: colors.text }]}>
              {priceLabel(item.purchaseMinor)}
            </Text>
            <Badge label={assessment.label} tone={assessment.tone} />
          </View>
          <Pressable
            accessibilityRole="button"
            onPress={onPress}
            style={{
              minHeight: 44,
              justifyContent: "center",
              paddingHorizontal: 8,
            }}
          >
            <Text style={[typography.bodyStrong, { color: colors.accent }]}>
              Szczegóły →
            </Text>
          </Pressable>
          {onWatch ? (
            <IconButton
              icon={watched ? "bookmark" : "bookmark-outline"}
              label={watched ? "Usuń z zapisanych" : "Zapisz ofertę"}
              active={watched}
              loading={watchLoading}
              disabled={watchDisabled}
              onPress={onWatch}
            />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}
