import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { MoneyValue } from '@/components/MoneyValue';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';
import { workspaceId } from '@/utils/config';
import { ACTIVE_DEAL_STATUSES } from '@/features/dashboard/summary';

export default function FlipsScreen() {
  const router = useRouter();
  const { colors, typography } = useTheme();
  const { columns, contentWidth } = useResponsiveLayout();
  const [status, setStatus] = useState('ALL');
  const deals = useQuery({ queryKey: ['deals', api.mode], queryFn: () => api.deals.list() });
  const items = deals.data?.items.filter(item => status === 'ALL' || (status === 'BOUGHT' ? ACTIVE_DEAL_STATUSES.includes(item.status) : item.status === status)) ?? [];
  return <AppScreen>
    <Header title="Moje flipy" subtitle="Zakupy, koszty i wyniki sprzedaży" rightSlot={<PrimaryButton label="Analityka" variant="secondary" onPress={() => router.push('/analytics')} />} />
    <DemoBanner />
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
      {[['ALL', 'Wszystkie'], ['BOUGHT', 'Aktywne'], ['SOLD', 'Sprzedane']].map(([value, label]) => <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected: status === value }} onPress={() => setStatus(value!)}
        style={{ minHeight: 40, justifyContent: 'center', paddingHorizontal: 16, borderRadius: 10, backgroundColor: status === value ? colors.accentMuted : colors.surface }}>
        <Text style={[typography.caption, { color: status === value ? colors.accent : colors.textMuted }]}>{label}</Text>
      </Pressable>)}
    </View>
    {api.mode === 'live' && !workspaceId() ? <Text style={[typography.caption, { color: colors.risk, marginBottom: 12 }]}>Brak skonfigurowanej przestrzeni transakcji.</Text> : null}
    {deals.isSuccess ? <Text style={[typography.caption, { color: colors.textMuted, marginBottom: 16 }]}>Pobrana strona: {deals.data.items.length} flipów.{deals.data.next_before_id ? ' Dostępne są kolejne transakcje; podsumowanie jest częściowe.' : ''}</Text> : null}
    {deals.isPending ? <LoadingSkeleton /> : deals.isError ? <ErrorState message={apiErrorMessage(deals.error)} onRetry={() => void deals.refetch()} /> :
      <FlatList key={columns} data={items} numColumns={columns} keyExtractor={item => item.id}
        columnWrapperStyle={columns > 1 ? { gap: 16 } : undefined} contentContainerStyle={{ gap: 16, paddingBottom: 16 }}
        refreshControl={<RefreshControl tintColor={colors.accent} refreshing={deals.isRefetching} onRefresh={() => void deals.refetch()} />}
        ListEmptyComponent={<EmptyState title="Brak flipów w tym widoku" description="Dodaj zakup z ekranu szczegółów oferty lub zmień filtr." />}
        renderItem={({ item }) => <Pressable accessibilityRole="button" accessibilityLabel={`Otwórz flip: ${item.title ?? item.id}`}
          onPress={() => router.push({ pathname: '/flips/[dealId]', params: { dealId: item.id } })}
          style={{ width: (contentWidth - (columns - 1) * 16) / columns, borderWidth: 1, borderRadius: 16, borderColor: colors.border, backgroundColor: colors.surface, padding: 20, gap: 16 }}>
          <View style={{ flexDirection: 'row', gap: 8, alignItems: 'flex-start' }}>
            <Text style={[typography.bodyStrong, { color: colors.text, flex: 1 }]} numberOfLines={2}>{item.title ?? item.id}</Text>
            <View style={{ backgroundColor: item.status === 'SOLD' ? colors.successBg : colors.accentMuted, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 }}>
              <Text style={[typography.caption, { color: item.status === 'SOLD' ? colors.success : colors.accent }]}>{item.status === 'SOLD' ? 'Sprzedany' : item.status === 'BOUGHT' ? 'Zakupiony' : item.status === 'LISTED' ? 'Wystawiony' : item.status}</Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', gap: 12 }}>
            <View style={{ flex: 1 }}><MoneyValue label="Zakup" amountMinor={item.purchase_minor} emptyLabel="Brak danych" /></View>
            <View style={{ flex: 1 }}><MoneyValue label="Koszty" amountMinor={item.cost_minor} emptyLabel="Brak danych" /></View>
          </View>
          <View style={{ flexDirection: 'row', gap: 12 }}>
            <View style={{ flex: 1 }}><MoneyValue label="Sprzedaż" amountMinor={item.sale_minor} emptyLabel={item.status === 'SOLD' ? 'Brak danych' : 'Jeszcze nie sprzedano'} /></View>
            <View style={{ flex: 1 }}><MoneyValue label="Wynik zrealizowany" amountMinor={item.realized_profit_minor} emptyLabel={item.status === 'SOLD' ? 'Brak danych' : 'Po sprzedaży'} tone="profit" /></View>
          </View>
          <Text style={[typography.caption, { color: colors.accent, marginTop: 4 }]}>Szczegóły i operacje →</Text>
        </Pressable>} />}
  </AppScreen>;
}
