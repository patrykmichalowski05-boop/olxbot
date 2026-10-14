import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { FinancialDeal } from '@/api/mappers/deal';
import { useTheme } from '@/theme/ThemeProvider';
import { formatMoneyMinor } from '@/utils/money';
import { EmptyState } from './EmptyState';

export function ProfitChart({ deals }: { deals: FinancialDeal[] }) {
  const { colors, typography } = useTheme();
  const rows = deals.filter(deal => deal.status === 'SOLD' && deal.realized_profit_minor != null && Number.isSafeInteger(deal.realized_profit_minor) && (!deal.currency || deal.currency === 'PLN')).slice(0, 8);
  const max = Math.max(...rows.map(deal => Math.abs(deal.realized_profit_minor!)), 1);
  if (!rows.length) return <EmptyState title="Brak danych do wykresu" description="Wyniki pojawią się po zarejestrowaniu sprzedaży." />;

  return <View accessibilityLabel="Wynik operacyjny sprzedanych flipów" style={{ gap: 18 }}>
    {rows.map(deal => {
      const profit = deal.realized_profit_minor!;
      const percentage = `${Math.abs(profit) / max * 100}%` as const;
      return <View key={deal.id} style={styles.row}>
        <Text style={[typography.caption, styles.title, { color: colors.text }]} numberOfLines={2}>{deal.title || deal.id}</Text>
        <View style={styles.plot}>
          <View style={[styles.half, { alignItems: 'flex-end', borderRightColor: colors.textMuted, borderRightWidth: 1, backgroundColor: colors.sidebar }]}>
            {profit < 0 ? <View style={[styles.bar, { width: percentage, backgroundColor: colors.loss }]} /> : null}
          </View>
          <View style={[styles.half, { backgroundColor: colors.sidebar }]}>
            {profit > 0 ? <View style={[styles.bar, { width: percentage, backgroundColor: colors.success }]} /> : null}
          </View>
        </View>
        <Text style={[typography.caption, styles.value, { color: profit < 0 ? colors.loss : colors.success, fontWeight: '600' }]}>{formatMoneyMinor(profit)}</Text>
      </View>;
    })}
    <Text style={[typography.caption, { color: colors.textMuted }]}>Punkt środkowy: 0 zł. Długość słupka odpowiada wynikowi transakcji. Maks. 8 sprzedanych flipów z pobranej strony.</Text>
  </View>;
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  title: { width: 100 },
  plot: { flex: 1, minWidth: 20, flexDirection: 'row', height: 18 },
  half: { flex: 1, justifyContent: 'center' },
  bar: { height: 12, borderRadius: 3 },
  value: { width: 90, textAlign: 'right' },
});
