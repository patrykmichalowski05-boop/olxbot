import React, { useMemo } from 'react';
import { Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';

import { api } from '@/api';
import { AppScreen } from '@/components/AppScreen';
import { Header } from '@/components/Header';
import { MoneyValue } from '@/components/MoneyValue';
import { useTheme } from '@/theme/ThemeProvider';

export default function AnalyticsScreen() {
  const { colors, spacing, typography, radii } = useTheme();
  const dealsQuery = useQuery({
    queryKey: ['deals', api.mode, 'analytics'],
    queryFn: () => api.deals.list(),
  });

  const stats = useMemo(() => {
    const items = dealsQuery.data?.items ?? [];
    let sold = 0;
    let profit = 0;
    let inventory = 0;
    let costs = 0;
    for (const deal of items) {
      costs += deal.total_costs_minor ?? 0;
      if (deal.status === 'SOLD') {
        sold += 1;
        profit += deal.profit_minor ?? 0;
      } else {
        inventory += deal.purchase_amount_minor ?? 0;
      }
    }
    return { sold, profit, inventory, costs };
  }, [dealsQuery.data]);

  return (
    <AppScreen scroll>
      <Header title="Analityka" showBack showNotifications={false} />
      <Text style={[typography.body, { color: colors.textMuted, marginBottom: spacing.lg }]}>
        Rzeczywiste wyniki z zapisanych flipów. Prognozy radaru są oddzielone.
      </Text>

      <View
        style={{
          backgroundColor: colors.surface,
          borderRadius: radii.md,
          padding: spacing.lg,
          gap: spacing.lg,
          borderWidth: 1,
          borderColor: colors.border,
        }}
      >
        <MoneyValue label="Zrealizowany zysk" amountMinor={stats.profit} emphasize />
        <MoneyValue label="Kapitał w zapasach" amountMinor={stats.inventory} />
        <Text style={[typography.bodyStrong, { color: colors.text }]}>
          Sprzedane przedmioty: {stats.sold}
        </Text>
        <MoneyValue label="Koszty łącznie" amountMinor={stats.costs} />
      </View>
    </AppScreen>
  );
}
