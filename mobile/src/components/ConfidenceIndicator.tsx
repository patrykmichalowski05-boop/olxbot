import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';

type Props = { confidence?: string | null };

export function ConfidenceIndicator({ confidence }: Props) {
  const { colors, typography } = useTheme();
  const label = confidence?.trim() || 'Brak oceny pewności';

  return (
    <View accessibilityRole="text">
      <Text style={[typography.caption, { color: colors.textMuted }]}>Pewność wyceny</Text>
      <Text style={[typography.bodyStrong, { color: colors.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({});
