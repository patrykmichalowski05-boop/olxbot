import React from "react";
import { Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/theme/ThemeProvider";
import type { IconName } from "./IconButton";

export type BadgeTone = "accent" | "success" | "warning" | "danger" | "neutral";
export function Badge({
  label,
  tone = "neutral",
  icon,
  accessibilityLabel,
}: {
  label: string;
  tone?: BadgeTone;
  icon?: IconName;
  accessibilityLabel?: string;
}) {
  const { colors, radii, typography } = useTheme();
  const palette = {
    accent: [colors.accent, colors.accentBg],
    success: [colors.success, colors.successBg],
    warning: [colors.risk, colors.riskBg],
    danger: [colors.loss, colors.lossBg],
    neutral: [colors.textMuted, colors.surfaceElevated],
  }[tone];
  return (
    <View
      accessibilityLabel={accessibilityLabel}
      style={{
        alignSelf: "flex-start",
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
        borderRadius: radii.pill,
        paddingHorizontal: 8,
        paddingVertical: 4,
        backgroundColor: palette[1],
        borderWidth: 1,
        borderColor: tone === "neutral" ? colors.border : `${palette[0]}33`,
        maxWidth: "100%",
      }}
    >
      {icon ? <Ionicons name={icon} size={12} color={palette[0]} /> : null}
      <Text
        style={[
          typography.caption,
          { color: palette[0], fontWeight: "700", flexShrink: 1 },
        ]}
      >
        {label}
      </Text>
    </View>
  );
}
