import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleProp,
  Text,
  ViewStyle,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/theme/ThemeProvider";
import type { IconName } from "./IconButton";

type Props = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "primary" | "secondary" | "ghost";
  style?: StyleProp<ViewStyle>;
  icon?: IconName;
};
export function PrimaryButton({
  label,
  onPress,
  disabled,
  loading,
  variant = "primary",
  style,
  icon,
}: Props) {
  const { colors, radii, spacing, typography } = useTheme();
  const foreground = variant === "primary" ? colors.onPrimary : colors.text;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{
        disabled: Boolean(disabled || loading),
        busy: Boolean(loading),
      }}
      aria-busy={Boolean(loading)}
      aria-disabled={Boolean(disabled || loading)}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        {
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "row",
          gap: spacing.sm,
          minHeight: 44,
          paddingVertical: spacing.md,
          paddingHorizontal: spacing.lg,
          borderRadius: radii.md,
          backgroundColor:
            variant === "primary"
              ? colors.primary
              : variant === "secondary"
                ? colors.surface
                : "transparent",
          borderColor: colors.border,
          borderWidth: variant === "secondary" ? 1 : 0,
          opacity: disabled ? 0.45 : pressed ? 0.75 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={foreground} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={18} color={foreground} /> : null}
          <Text
            style={[
              typography.bodyStrong,
              { color: foreground, textAlign: "center", flexShrink: 1 },
            ]}
          >
            {label}
          </Text>
        </>
      )}
    </Pressable>
  );
}
