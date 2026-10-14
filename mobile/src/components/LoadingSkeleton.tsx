import React from 'react';
import { StyleSheet, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';

type Props = { rows?: number };

export function LoadingSkeleton({ rows = 4 }: Props) {
  const { colors, radii, spacing } = useTheme();

  return (
    <View style={{ gap: spacing.md }}>
      {Array.from({ length: rows }).map((_, index) => (
        <View
          key={index}
          style={[
            styles.card,
            {
              backgroundColor: colors.surface,
              borderRadius: radii.md,
              height: 112,
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { opacity: 0.55 },
});
