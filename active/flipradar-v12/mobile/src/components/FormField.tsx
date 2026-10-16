import React, { useState } from "react";
import {
  Text,
  TextInput,
  TextInputProps,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { useTheme } from "@/theme/ThemeProvider";

type Props = TextInputProps & {
  label: string;
  error?: string;
  hint?: string;
  compact?: boolean;
  containerStyle?: StyleProp<ViewStyle>;
};
export function FormField({
  label,
  error,
  hint,
  compact,
  containerStyle,
  style,
  ...rest
}: Props) {
  const { colors, radii, spacing, typography } = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View
      style={[
        { gap: 6, marginBottom: compact ? 0 : spacing.md },
        containerStyle,
      ]}
    >
      <Text
        style={[
          typography.caption,
          { fontWeight: "600", color: colors.textMuted },
        ]}
      >
        {label}
      </Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.textMuted}
        selectionColor={colors.accent}
        style={[
          typography.body,
          {
            minHeight: 44,
            borderWidth: 1,
            color: colors.text,
            borderColor: error
              ? colors.loss
              : focused
                ? colors.focus
                : colors.border,
            backgroundColor: colors.surface,
            borderRadius: radii.md,
            padding: spacing.md,
          },
          style,
        ]}
        {...rest}
        onFocus={(event) => {
          setFocused(true);
          rest.onFocus?.(event);
        }}
        onBlur={(event) => {
          setFocused(false);
          rest.onBlur?.(event);
        }}
      />
      {error ? (
        <Text
          style={[typography.caption, { color: colors.loss }]}
          accessibilityLiveRegion="polite"
        >
          {error}
        </Text>
      ) : hint ? (
        <Text style={[typography.caption, { color: colors.textMuted }]}>
          {hint}
        </Text>
      ) : null}
    </View>
  );
}
