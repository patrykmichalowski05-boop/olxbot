import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';
import { PrimaryButton } from './PrimaryButton';

type Props = {
  message: string;
  onRetry?: () => void;
};

export function ErrorState({ message, onRetry }: Props) {
  const { colors, spacing, typography } = useTheme();

  return (
    <View style={[styles.wrap, { gap: spacing.md, padding: spacing.lg }]}>
      <Text style={[typography.headline, { color: colors.loss }]}>Coś poszło nie tak</Text>
      <Text style={[typography.body, { color: colors.textMuted }]}>{message}</Text>
      {onRetry ? <PrimaryButton label="Spróbuj ponownie" onPress={onRetry} variant="secondary" /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'stretch' },
});
