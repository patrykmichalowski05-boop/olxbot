import React from 'react';
import { StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';

type Props = TextInputProps & {
  label: string;
  error?: string;
  hint?: string;
};

export function FormField({ label, error, hint, style, ...rest }: Props) {
  const { colors, radii, spacing, typography } = useTheme();

  return (
    <View style={{ gap: spacing.xs, marginBottom: spacing.md }}>
      <Text style={[typography.bodyStrong, { color: colors.text }]}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.textMuted}
        style={[
          styles.input,
          typography.body,
          {
            color: colors.text,
            borderColor: error ? colors.loss : colors.border,
            backgroundColor: colors.surface,
            borderRadius: radii.md,
            padding: spacing.md,
          },
          style,
        ]}
        {...rest}
      />
      {error ? (
        <Text style={[typography.caption, { color: colors.loss }]} accessibilityLiveRegion="polite">
          {error}
        </Text>
      ) : hint ? (
        <Text style={[typography.caption, { color: colors.textMuted }]}>{hint}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  input: { borderWidth: 1, minHeight: 48 },
});
