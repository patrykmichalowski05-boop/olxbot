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
};

export function MoneyValue({
  label,
  amountMinor,
  roiBps,
  emphasize,
  emptyLabel,
}: Props) {
  const { colors, typography } = useTheme();
  const valueStyle = emphasize ? typography.money : typography.moneySmall;

  return (
    <View style={styles.wrap}>
      {label ? (
        <Text style={[typography.caption, { color: colors.textMuted }]}>{label}</Text>
      ) : null}
      <Text
        accessibilityLabel={label ? `${label}: ${formatMoneyMinor(amountMinor, 'PLN', { emptyLabel })}` : undefined}
        style={[valueStyle, { color: colors.text }]}
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
