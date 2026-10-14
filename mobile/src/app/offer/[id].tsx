import React from 'react';
import { Linking, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { ConfidenceIndicator } from '@/components/ConfidenceIndicator';
import { DecisionBadge } from '@/components/DecisionBadge';
import { DemoBanner } from '@/components/DemoBanner';
import { ErrorState } from '@/components/ErrorState';
import { Header } from '@/components/Header';
import { ListingImage } from '@/components/ListingImage';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { MoneyValue } from '@/components/MoneyValue';
import { Panel } from '@/components/Panel';
import { PrimaryButton } from '@/components/PrimaryButton';
import { ResponsiveGrid } from '@/components/ResponsiveGrid';
import { RiskList } from '@/components/RiskList';
import { SourceStatus } from '@/components/SourceStatus';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';
import { formatUserDateTime } from '@/utils/datetime';
import { formatMoneyMinor } from '@/utils/money';

export default function OfferDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { colors, typography } = useTheme();
  const { isMobile, contentWidth } = useResponsiveLayout();
  const detail = useQuery({ queryKey: ['offer', id, api.mode], enabled: Boolean(id), queryFn: () => api.opportunityDetail(String(id)) });
  const watch = useMutation({
    mutationFn: () => api.watchlist.add(`listing:${id}`, detail.data?.title ?? `Oferta ${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });
  if (detail.isPending) return <AppScreen><Header title="Szczegóły oferty" showBack /><LoadingSkeleton rows={3} /></AppScreen>;
  if (detail.isError || !detail.data) return <AppScreen><Header title="Szczegóły oferty" showBack /><ErrorState message={detail.data === null ? 'Oferta nie istnieje lub wygasła.' : apiErrorMessage(detail.error)} onRetry={() => void detail.refetch()} /></AppScreen>;
  const item = detail.data;

  return <AppScreen scroll>
    <Header title="Szczegóły oferty" showBack showNotifications={false} />
    <DemoBanner />
    <View style={{ gap: 20 }}>
      <View style={{ flexDirection: isMobile ? 'column' : 'row', alignItems: 'flex-start', gap: 16 }}>
        <Panel title={item.title} style={{ flex: isMobile ? undefined : 2, width: isMobile ? '100%' : undefined }}>
          <ListingImage item={item} style={{ height: item.imageUrl ? 220 : 88, borderRadius: 12 }} />
          {item.variant ? <Text style={[typography.body, { color: colors.textMuted }]}>{item.variant}</Text> : null}
          <SourceStatus platform={item.platform} status={item.sourceStatus} />
          <ResponsiveGrid columns={contentWidth >= 1200 ? 4 : 2}>
            <MoneyValue label="Cena zakupu" amountMinor={item.purchaseMinor} />
            <MoneyValue label="Prognoza odsprzedaży" amountMinor={item.hasValuation ? item.baseScenario?.resaleMinor ?? item.resaleRange?.highMinor : null} emptyLabel="Brak wyceny" />
            <MoneyValue label="Koszty (prognoza)" amountMinor={item.baseScenario?.costsMinor} emptyLabel="Brak danych" />
            <MoneyValue label="Potencjalny wynik operacyjny" amountMinor={item.hasValuation ? item.operatingProfitMinor : null} roiBps={item.hasValuation ? item.roiBps : null} emptyLabel="Brak wyceny" tone="profit" />
          </ResponsiveGrid>
          <MoneyValue label="Maks. cena zakupu" amountMinor={item.maxBuyMinor} emptyLabel="Brak danych" />
        </Panel>
        <View style={{ flex: isMobile ? undefined : 1, width: isMobile ? '100%' : undefined, minWidth: 0, gap: 16 }}>
          <Panel title="Rekomendacja AI">
            <DecisionBadge decision={item.decision} />
            {item.decisionReason ? <Text style={[typography.body, { color: colors.text }]}>{item.decisionReason}</Text> : null}
            <ConfidenceIndicator confidence={item.confidence} />
            <Text style={[typography.caption, { color: colors.textMuted }]}>Ostatnia weryfikacja: {formatUserDateTime(item.verifiedAt)}</Text>
          </Panel>
          <Panel title="Działania">
            <PrimaryButton label="Obserwuj" variant="secondary" loading={watch.isPending} onPress={() => watch.mutate()} />
            {watch.isSuccess ? <Text accessibilityLiveRegion="polite" style={[typography.caption, { color: colors.accent }]}>Dodano do obserwowanych.</Text> : null}
            {watch.isError ? <Text accessibilityRole="alert" style={[typography.caption, { color: colors.loss }]}>{apiErrorMessage(watch.error)}</Text> : null}
            <PrimaryButton label="Otwórz ogłoszenie" variant="secondary" disabled={!item.url} onPress={() => { if (item.url) void Linking.openURL(item.url).catch(() => undefined); }} />
            <PrimaryButton label="Dodaj do moich flipów (zakup)" onPress={() => router.push({ pathname: '/purchase/[listingId]', params: { listingId: String(item.listingId ?? id) } })} />
            <PrimaryButton label="Analizuj ponownie" variant="secondary" onPress={() => router.push('/analyze')} />
          </Panel>
        </View>
      </View>
      <ResponsiveGrid columns={isMobile ? 1 : 2}>
        <Panel><RiskList title="Ryzyka" items={item.risks} /></Panel>
        <Panel><RiskList title="Niewiadome" items={item.unknowns} emptyLabel="Brak listy braków" /></Panel>
      </ResponsiveGrid>
      {item.conservativeScenario && item.baseScenario ? <Panel title="Scenariusze" subtitle="Wyceny są prognozą. Cena negocjowana w scenariuszu jest hipotetyczna.">
        <ResponsiveGrid columns={isMobile ? 1 : 2}>
          {[item.conservativeScenario, item.baseScenario].map(scenario => <View key={scenario.label} style={{ gap: 12, backgroundColor: colors.sidebar, padding: 16, borderRadius: 12 }}>
            <Text style={[typography.bodyStrong, { color: colors.accent }]}>{scenario.label}</Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 20 }}>
              <MoneyValue label="Zakup" amountMinor={scenario.purchaseMinor} />
              <MoneyValue label="Odsprzedaż" amountMinor={item.hasValuation ? scenario.resaleMinor : null} />
              <MoneyValue label="Zysk operacyjny" amountMinor={item.hasValuation ? scenario.profitMinor : null} tone="profit" />
            </View>
          </View>)}
        </ResponsiveGrid>
      </Panel> : null}
      {item.specs.length ? <Panel title="Parametry">{item.specs.map((spec, index) => <View key={index} style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 }}>
        <Text style={[typography.caption, { color: colors.textMuted }]}>{spec.label}</Text><Text style={[typography.bodyStrong, { color: colors.text }]}>{spec.value}</Text>
      </View>)}</Panel> : null}
      <Panel title="Historia ceny">
        {item.priceHistory.length ? item.priceHistory.map((point, index) => <View key={`${point.at}-${index}`} style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 }}>
          <Text style={[typography.caption, { color: colors.textMuted }]}>{formatUserDateTime(point.at)}</Text>
          <Text style={[typography.bodyStrong, { color: colors.text }]}>{formatMoneyMinor(point.priceMinor, 'PLN', { emptyLabel: 'Brak danych' })}</Text>
        </View>) : <Text style={[typography.caption, { color: colors.textMuted }]}>Brak danych o historii ceny.</Text>}
      </Panel>
    </View>
  </AppScreen>;
}
