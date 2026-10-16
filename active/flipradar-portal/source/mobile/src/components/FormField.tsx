import React, { useState } from 'react';
import { Text, TextInput, TextInputProps, View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';

type Props = TextInputProps & { label: string; error?: string; hint?: string };
export function FormField({ label, error, hint, style, ...rest }: Props) {
  const { colors, radii, spacing, typography } = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: spacing.sm, marginBottom: spacing.lg }}>
      <Text style={[typography.bodyStrong, { color: colors.text }]}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.textMuted}
        selectionColor={colors.accent}
        style={[
          typography.body,
          {
            minHeight: 54,
            borderWidth: 1,
            color: colors.text,
            borderColor: error ? colors.loss : focused ? colors.accent : colors.border,
            backgroundColor: focused ? colors.accentBg : colors.background,
            borderRadius: radii.lg,
            padding: spacing.lg,
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
        <Text style={[typography.caption, { color: colors.textMuted }]}>{hint}</Text>
      ) : null}
    </View>
  );
}
