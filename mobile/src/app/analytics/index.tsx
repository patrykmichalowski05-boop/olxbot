import React from 'react';
import { Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { ErrorState } from '@/components/ErrorState';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { MetricCard } from '@/components/MetricCard';
import { Panel } from '@/components/Panel';
import { PrimaryButton } from '@/components/PrimaryButton';
import { ProfitChart } from '@/components/ProfitChart';
import { ResponsiveGrid } from '@/components/ResponsiveGrid';
import { summarizeDeals } from '@/features/dashboard/summary';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';
import { formatMoneyMinor } from '@/utils/money';

export default function AnalyticsScreen() {
  const { colors, typography } = useTheme();
  const { isMobile, isDesktop } = useResponsiveLayout();
  const deals = useQuery({ queryKey: ['deals', api.mode], queryFn: () => api.deals.list() });
  const stats = summarizeDeals(deals.isSuccess ? deals.data.items : undefined);
  const money = (value: number | null) => value === null ? null : formatMoneyMinor(value);
  return <AppScreen scroll>
    <Header title="Analityka" subtitle="Kapitał, koszty i rzeczywiste wyniki" showBack showNotifications={false} rightSlot={<PrimaryButton label="Odśwież" variant="secondary" onPress={() => void deals.refetch()} />} />
    <DemoBanner />
    <View style={{ gap: 24 }}>
      <ResponsiveGrid columns={isDesktop ? 4 : 2}>
        <MetricCard label="Zrealizowany zysk" value={money(stats.profitMinor)} icon="trending-up-outline" loading={deals.isPending} help="Suma wyników sprzedanych flipów" tone={stats.profitMinor !== null && stats.profitMinor < 0 ? 'loss' : 'success'} />
        <MetricCard label="Kapitał w zapasach" value={money(stats.inventoryMinor)} icon="briefcase-outline" loading={deals.isPending} help="Zakupy aktywnych flipów" />
        <MetricCard label="Sprzedane przedmioty" value={stats.sold === null ? null : String(stats.sold)} icon="checkmark-circle-outline" loading={deals.isPending} help="Status sprzedaży z backendu" />
        <MetricCard label="Koszty łącznie" value={money(stats.costsMinor)} icon="receipt-outline" loading={deals.isPending} help="Koszty pobranych transakcji" />
      </ResponsiveGrid>
      <Text style={[typography.caption, { color: colors.textMuted }]}>Wskaźniki obejmują pobraną stronę (do 30 flipów w LIVE).{deals.data?.next_before_id ? ' Podsumowanie jest częściowe — istnieją kolejne strony.' : ''} Brak kwoty lub statusu oznacza brak danych do podsumowania.</Text>
      {deals.isError ? <ErrorState message={apiErrorMessage(deals.error)} onRetry={() => void deals.refetch()} /> : null}
      <ResponsiveGrid columns={isMobile ? 1 : 2}>
        <Panel title="Zysk na sprzedanym przedmiocie" subtitle="Każdy słupek przedstawia jedną transakcję">
          {deals.isPending ? <LoadingSkeleton rows={3} /> : deals.isSuccess ? <ProfitChart deals={deals.data.items} /> : <Text style={[typography.body, { color: colors.textMuted }]}>Brak danych do wykresu</Text>}
        </Panel>
        <Panel title="Status transakcji" subtitle="Zakres tej samej pobranej strony">
          {[['Aktywne flipy', stats.active], ['Sprzedane flipy', stats.sold]].map(([label, value]) => <View key={String(label)} style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 16, paddingVertical: 12, borderBottomWidth: 1, borderColor: colors.border }}>
            <Text style={[typography.body, { color: colors.textMuted }]}>{label}</Text>
            <Text style={[typography.bodyStrong, { color: colors.text }]}>{value ?? 'Brak danych'}</Text>
          </View>)}
          <Text style={[typography.caption, { color: colors.textMuted }]}>Prognozy okazji są oddzielone od wyniku już sprzedanych przedmiotów. Wykres korzysta z zapisanych wyników; nie odtwarza brakujących kwot ani dat sprzedaży.</Text>
        </Panel>
      </ResponsiveGrid>
    </View>
  </AppScreen>;
}
