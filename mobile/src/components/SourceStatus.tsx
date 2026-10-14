import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';

type Props = {
  platform: string;
  status: string;
};

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Aktywne ogłoszenie',
  UNAVAILABLE: 'Niedostępne',
  IMPORT_ONLY: 'Tylko import',
  UNKNOWN: 'Status nieznany',
};

export function SourceStatus({ platform, status }: Props) {
  const { colors, typography, radii, spacing } = useTheme();
  const key = status.toUpperCase();
  const label = STATUS_LABELS[key] ?? status;

  const color =
    key === 'UNAVAILABLE' || key === 'IMPORT_ONLY'
      ? colors.loss
      : key === 'ACTIVE'
        ? colors.success
        : colors.textMuted;

  return (
    <View style={[styles.row, { gap: spacing.sm }]}>
      <Text style={[typography.caption, { color: colors.textMuted }]}>{platform}</Text>
      <View style={[styles.chip, { borderColor: colors.border, borderRadius: radii.pill }]}>
        <Text style={[typography.caption, { color }]}>{label}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap' },
  chip: {
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
});
