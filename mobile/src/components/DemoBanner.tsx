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
          backgroundColor: colors.riskBg,
          borderColor: colors.risk,
          borderRadius: radii.sm,
          padding: spacing.sm,
          marginBottom: spacing.sm,
        },
      ]}
    >
      <Text style={[typography.caption, { color: colors.risk, fontWeight: '600' }]}>
        TRYB DEMO — dane przykładowe, zapis finansowy nie trafia do API live.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { borderWidth: 1 },
});
