import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api';
import type { UniversalWatchItem } from '@/api/endpoints/universal';
import { useTheme } from '@/theme/ThemeProvider';
import { formatRelativeSync, formatUserDateTime } from '@/utils/datetime';
import { formatMoneyMinor } from '@/utils/money';
import { MoneyValue } from './MoneyValue';
import { PrimaryButton } from './PrimaryButton';

export function WatchedCard({ item, onRemove, pending }: { item: UniversalWatchItem; onRemove: () => void; pending: boolean }) {
  const { colors, typography } = useTheme();
  // Only a declared legacy listing reference can be used with the v1 detail API.
  const listingId = /^listing:(\d+)$/.exec(item.listing_key)?.[1];
  const detail = useQuery({ queryKey: ['watch-price', item.listing_key, api.mode], queryFn: () => api.opportunityDetail(listingId!), enabled: Boolean(listingId) });
  const history = detail.data?.priceHistory ?? [];
  return <View testID={`watched-card-${item.listing_key}`} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
    <Text style={[typography.bodyStrong, { color: colors.text }]} numberOfLines={2}>{item.label}</Text>
    <View style={styles.metrics}>
      <MoneyValue label="Aktualna cena" amountMinor={item.price_minor ?? detail.data?.purchaseMinor} emptyLabel="Brak danych" />
      <MoneyValue label="Próg zakupu" amountMinor={item.threshold_minor} emptyLabel="Brak danych" />
    </View>
    <View style={[styles.history, { borderColor: colors.border }]}>
      <Text style={[typography.caption, { color: colors.textMuted }]}>Zmiany cen</Text>
      {history.length ? history.slice(-3).map((point, index) => <Text key={`${point.at}-${index}`} style={[typography.caption, { color: colors.text }]}>{formatUserDateTime(point.at)} · {formatMoneyMinor(point.priceMinor, 'PLN', { emptyLabel: 'Brak danych' })}</Text>) :
        <Text style={[typography.caption, { color: colors.textMuted }]}>{detail.isFetching ? 'Pobieranie historii…' : 'Brak danych o historii ceny'}</Text>}
    </View>
    <Text style={[typography.caption, { color: colors.textMuted }]}>Sprawdzone: {formatRelativeSync(item.updated)}</Text>
    <PrimaryButton label="Usuń z obserwowanych" variant="secondary" onPress={onRemove} loading={pending} />
  </View>;
}

const styles = StyleSheet.create({
  card: { flex: 1, borderWidth: 1, borderRadius: 16, padding: 16, gap: 16 },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: 20 },
  history: { paddingTop: 12, borderTopWidth: 1, gap: 6 },
});
