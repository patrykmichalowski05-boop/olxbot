import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { Header } from '@/components/Header';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { MetricCard } from '@/components/MetricCard';
import { NotificationCard } from '@/components/NotificationCard';
import { OpportunityRow } from '@/components/OpportunityRow';
import { Panel } from '@/components/Panel';
import { PrimaryButton } from '@/components/PrimaryButton';
import { ProfitChart } from '@/components/ProfitChart';
import { ResponsiveGrid } from '@/components/ResponsiveGrid';
import { summarizeDeals, summarizeRadar } from '@/features/dashboard/summary';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';
import { formatMoneyMinor } from '@/utils/money';
import { workspaceId } from '@/utils/config';

export default function DashboardScreen() {
  const router = useRouter();
  const { colors, typography } = useTheme();
  const { isMobile, isDesktop } = useResponsiveLayout();
  const radar = useQuery({ queryKey: ['dashboard', 'radar', api.mode], queryFn: ({ signal }) => api.radarPage({ limit: 30, signal }) });
  const deals = useQuery({ queryKey: ['deals', api.mode], queryFn: () => api.deals.list() });
  const notifications = useQuery({ queryKey: ['dashboard', 'notifications', api.mode, workspaceId()], queryFn: () => api.notificationsPage() });
  const radarStats = summarizeRadar(radar.isSuccess ? radar.data.items : undefined);
  const dealStats = summarizeDeals(deals.isSuccess ? deals.data.items : undefined);
  const count = (value: number | null) => value === null ? null : String(value);
  const link = (label: string, onPress: () => void) => <Pressable accessibilityRole="button" onPress={onPress} style={{ minHeight: 44, justifyContent: 'center' }}><Text style={[typography.caption, { color: colors.accent, fontWeight: '600' }]}>{label}</Text></Pressable>;
  const attention = radar.data?.items.filter(item => ['BUY_CANDIDATE', 'NEGOTIATE', 'REVIEW'].includes(item.decision)) ?? [];

  return <AppScreen scroll>
    <Header title="Dashboard" subtitle="Przegląd okazji i Twoich flipów" rightSlot={<PrimaryButton label="Odśwież" variant="secondary" onPress={() => { void radar.refetch(); void deals.refetch(); void notifications.refetch(); }} />} />
    <DemoBanner />
    <View style={{ gap: 24 }}>
      <ResponsiveGrid columns={isDesktop ? 4 : 2}>
        <MetricCard label="Aktywne oferty" icon="radio-outline" value={count(radarStats.active)} loading={radar.isPending} help={radarStats.active === null ? 'Brak potwierdzonego statusu ofert' : 'Na pobranej stronie radaru'} />
        <MetricCard label="Wymagają uwagi" icon="alert-circle-outline" value={count(radarStats.attention)} loading={radar.isPending} tone="warning" help="Zakup, negocjacja lub weryfikacja · pobrane oferty" />
        <MetricCard label="Aktywne flipy" icon="briefcase-outline" value={count(dealStats.active)} loading={deals.isPending} help="Zakupione i wystawione · pobrana strona flipów" />
        <MetricCard label="Zrealizowany zysk" icon="trending-up-outline" value={dealStats.profitMinor === null ? null : formatMoneyMinor(dealStats.profitMinor)} loading={deals.isPending}
          tone={dealStats.profitMinor !== null && dealStats.profitMinor < 0 ? 'loss' : 'success'} help="Wynik sprzedanych flipów · pobrana strona" />
      </ResponsiveGrid>
      <Text style={[typography.caption, { color: colors.textMuted }]}>Podsumowanie dotyczy pierwszej strony każdego źródła (do 30 rekordów w LIVE). Brak danych oznacza brak potwierdzonego wyniku.{deals.data?.next_before_id ? ' Dostępne są dalsze transakcje.' : ''}</Text>
      <View style={{ flexDirection: isMobile ? 'column' : 'row', gap: 16, alignItems: 'flex-start' }}>
        <View style={{ flex: isMobile ? undefined : isDesktop ? 2 : 1, width: isMobile ? '100%' : undefined, minWidth: 0 }}>
          <Panel title="Ostatnio znalezione" subtitle="Najnowsze oferty z radaru" right={link('Cały radar', () => router.push('/radar'))}>
            {radar.isPending ? <LoadingSkeleton rows={3} /> : radar.isError ? <ErrorState message={apiErrorMessage(radar.error)} onRetry={() => void radar.refetch()} /> :
              radar.data.items.length ? <View>{radar.data.items.slice(0, 5).map(item => <OpportunityRow key={item.id} item={item} onPress={() => router.push({ pathname: '/offer/[id]', params: { id: String(item.listingId ?? item.snapshotId) } })} />)}</View> :
              <EmptyState title="Brak znalezionych ofert" description="Nowe oferty pojawią się po odświeżeniu radaru." />}
          </Panel>
        </View>
        <View style={{ flex: isMobile ? undefined : 1, width: isMobile ? '100%' : undefined, minWidth: 0, gap: 16 }}>
          <Panel title="Ostatnie powiadomienia" right={link('Skrzynka', () => router.push('/notifications'))}>
            {notifications.isPending ? <LoadingSkeleton rows={2} /> : notifications.isError ? <ErrorState message={apiErrorMessage(notifications.error)} onRetry={() => void notifications.refetch()} /> :
              notifications.data.items.length ? notifications.data.items.slice(0, 3).map(item => <NotificationCard key={item.id} item={item} compact />) :
              <EmptyState title="Brak powiadomień" description="Zdarzenia pojawią się tutaj po ich zapisaniu." />}
          </Panel>
          <Panel title="Analiza własnej oferty" subtitle="Sprawdź przedmiot, który znalazłeś poza radarem.">
            <PrimaryButton label="Otwórz analizę AI" onPress={() => router.push('/analyze')} />
          </Panel>
        </View>
      </View>
      <ResponsiveGrid columns={isMobile ? 1 : 2}>
        <Panel title="Wyniki sprzedanych flipów" subtitle="Zysk operacyjny zwrócony przez backend" right={link('Analityka', () => router.push('/analytics'))}>
          {deals.isPending ? <LoadingSkeleton rows={2} /> : deals.isError ? <ErrorState message={apiErrorMessage(deals.error)} onRetry={() => void deals.refetch()} /> : <ProfitChart deals={deals.data.items} />}
        </Panel>
        <Panel title="Okazje wymagające uwagi" subtitle="Kandydaci do zakupu, negocjacji i weryfikacji">
          {radar.isPending ? <LoadingSkeleton rows={2} /> : radar.isError ? <ErrorState message={apiErrorMessage(radar.error)} onRetry={() => void radar.refetch()} /> :
            attention.length ? attention.slice(0, 3).map(item => <OpportunityRow key={item.id} item={item} onPress={() => router.push({ pathname: '/offer/[id]', params: { id: String(item.listingId ?? item.snapshotId) } })} />) : <EmptyState title="Brak ofert wymagających uwagi" />}
        </Panel>
      </ResponsiveGrid>
    </View>
  </AppScreen>;
}
