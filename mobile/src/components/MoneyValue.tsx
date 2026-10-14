import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';
import { formatMoneyMinor, formatRoiBps } from '@/utils/money';

type Props = {
  label?: string;
  amountMinor: number | null | undefined;
  roiBps?: number | null;
  emphasize?: boolean;
  emptyLabel?: string;
  tone?: 'default' | 'profit';
};

export function MoneyValue({
  label,
  amountMinor,
  roiBps,
  emphasize,
  emptyLabel,
  tone = 'default',
}: Props) {
  const { colors, typography } = useTheme();
  const valueStyle = emphasize ? typography.money : typography.moneySmall;
  const color = tone === 'profit' && amountMinor != null
    ? amountMinor > 0 ? colors.success : amountMinor < 0 ? colors.loss : colors.text
    : colors.text;

  return (
    <View style={styles.wrap}>
      {label ? (
        <Text style={[typography.caption, { color: colors.textMuted }]}>{label}</Text>
      ) : null}
      <Text
        accessibilityLabel={label ? `${label}: ${formatMoneyMinor(amountMinor, 'PLN', { emptyLabel })}` : undefined}
        style={[valueStyle, { color }]}
      >
        {formatMoneyMinor(amountMinor, 'PLN', { emptyLabel })}
      </Text>
      {roiBps !== undefined ? (
        <Text style={[typography.caption, { color: colors.textMuted }]}>
          ROI {formatRoiBps(roiBps)}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 2 },
});
