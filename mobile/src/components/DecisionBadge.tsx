import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';
import { decisionLabel, decisionTone } from '@/utils/labels';

type Props = { decision: string };

export function DecisionBadge({ decision }: Props) {
  const { colors, radii, typography } = useTheme();
  const tone = decisionTone(decision);

  const palette =
    tone === 'success'
      ? { fg: colors.success, bg: colors.successBg }
      : tone === 'risk'
        ? { fg: colors.risk, bg: colors.riskBg }
        : tone === 'loss'
          ? { fg: colors.loss, bg: colors.lossBg }
          : { fg: colors.textMuted, bg: colors.surfaceElevated };

  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`Decyzja: ${decisionLabel(decision)}`}
      style={[styles.badge, { backgroundColor: palette.bg, borderRadius: radii.pill }]}
    >
      <Text style={[typography.caption, { color: palette.fg, fontWeight: '600' }]}>
        {decisionLabel(decision)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
});
