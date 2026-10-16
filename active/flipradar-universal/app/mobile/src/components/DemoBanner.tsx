import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/features/auth/AuthContext';
import { useTheme } from '@/theme/ThemeProvider';

export function DemoBanner() {
  const { mode } = useAuth();
  const { colors, spacing, typography, radii } = useTheme();

  if (mode !== 'demo') {
    return null;
  }

  return (
    <View
      accessibilityRole="text"
      style={[
        styles.banner,
        {
          backgroundColor: colors.accentBg,
          borderColor: colors.accentMuted,
          borderRadius: radii.sm,
          padding: spacing.sm,
          marginBottom: spacing.sm,
        },
      ]}
    >
      <Text style={[typography.caption, { color: colors.accent, fontWeight: '600' }]}>
        Tryb demo · Dane przykładowe
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { borderWidth: 1 },
});
