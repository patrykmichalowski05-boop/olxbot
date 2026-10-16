import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/theme/ThemeProvider';
import type { IconName } from './IconButton';

export function StatCard({
  label,
  value,
  icon,
  accent = false,
  wide = false,
  description,
}: {
  label: string;
  value: string;
  icon: IconName;
  accent?: boolean;
  wide?: boolean;
  description?: string;
}) {
  const { colors, radii, typography, spacing } = useTheme();
  return (
    <View
      accessibilityLabel={`${label}: ${value}${description ? `. ${description}` : ''}`}
      style={[
        styles.card,
        {
          backgroundColor: accent ? colors.accentBg : colors.surface,
          flexBasis: wide ? '22%' : '46%',
          borderColor: accent ? colors.accentMuted : colors.border,
          borderRadius: radii.lg,
          padding: spacing.md,
        },
      ]}
    >
      <View style={styles.label}>
        <Ionicons
          name={icon}
          size={14}
          color={accent ? colors.accent : colors.textSubtle}
        />
        <Text style={[typography.caption, { color: colors.textMuted, flexShrink: 1 }]}>
          {label}
        </Text>
      </View>
      <Text
        style={[
          typography.moneySmall,
          { color: accent ? colors.accent : colors.text, fontVariant: ['tabular-nums'] },
        ]}
      >
        {value}
      </Text>
    </View>
  );
}
const styles = StyleSheet.create({
  card: { flexGrow: 1, minWidth: 0, borderWidth: 1, gap: 4 },
  label: { flexDirection: 'row', alignItems: 'center', gap: 6 },
});
