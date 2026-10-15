import React from 'react';
import { Linking, ScrollView, Text, View } from 'react-native';
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
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { MoneyValue } from '@/components/MoneyValue';
import { PrimaryButton } from '@/components/PrimaryButton';
import { RiskList } from '@/components/RiskList';
import { SourceStatus } from '@/components/SourceStatus';
import { useTheme } from '@/theme/ThemeProvider';
import { formatUserDateTime } from '@/utils/datetime';

export default function OfferDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { colors, spacing, typography, radii } = useTheme();

  const detailQuery = useQuery({
    queryKey: ['offer', id, api.mode],
    enabled: Boolean(id),
    queryFn: () => api.opportunityDetail(String(id)),
  });

  const watchMutation = useMutation({
    mutationFn: () =>
      api.watchlist.add(`listing:${id}`, detailQuery.data?.title ?? `Oferta ${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  if (detailQuery.isLoading) {
    return (
      <AppScreen>
        <LoadingSkeleton rows={3} />
      </AppScreen>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <AppScreen>
        <ErrorState
          message={
            detailQuery.data === null
              ? 'Oferta nie istnieje lub wygasła.'
              : apiErrorMessage(detailQuery.error)
          }
          onRetry={() => detailQuery.refetch()}
        />
      </AppScreen>
    );
  }

  const item = detailQuery.data;

  return (
    <AppScreen scroll padded={false}>
      <View style={{ paddingHorizontal: spacing.lg }}>
        <Header title="Szczegóły oferty" showBack showNotifications={false} />
        <DemoBanner />
      </View>

      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg }}>
        <Text style={[typography.headline, { color: colors.text }]}>{item.title}</Text>
        {item.variant ? (
          <Text style={[typography.body, { color: colors.textMuted }]}>{item.variant}</Text>
        ) : null}
        <SourceStatus platform={item.platform} status={item.sourceStatus} />

        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 16 }}>
          <MoneyValue label="Cena zakupu" amountMinor={item.purchaseMinor} emphasize />
          <MoneyValue
            label="Prognoza odsprzedaży"
            amountMinor={item.baseScenario?.resaleMinor ?? item.resaleRange?.highMinor ?? null}
            emptyLabel="Brak wyceny"
          />
          <MoneyValue
            label="Koszty (prognoza)"
            amountMinor={item.baseScenario?.costsMinor ?? null}
            emptyLabel="—"
          />
          <MoneyValue
            label="Potencjalny wynik operacyjny"
            amountMinor={item.operatingProfitMinor}
            roiBps={item.roiBps}
            emptyLabel="Brak wyceny"
          />
          <MoneyValue label="Max buy" amountMinor={item.maxBuyMinor} emptyLabel="—" />
        </View>

        <View style={{ gap: spacing.sm }}>
          <DecisionBadge decision={item.decision} />
          {item.decisionReason ? (
            <Text style={[typography.body, { color: colors.text }]}>{item.decisionReason}</Text>
          ) : null}
          <ConfidenceIndicator confidence={item.confidence} />
          <Text style={[typography.caption, { color: colors.textMuted }]}>
            Ostatnia weryfikacja: {formatUserDateTime(item.verifiedAt)}
          </Text>
        </View>

        <RiskList title="Ryzyka" items={item.risks} />
        <RiskList title="Niewiadome" items={item.unknowns} emptyLabel="Brak listy braków" />

        {item.conservativeScenario && item.baseScenario ? (
          <View
            style={{
              backgroundColor: colors.surface,
              borderRadius: radii.md,
              padding: spacing.md,
              gap: spacing.sm,
              borderWidth: 1,
              borderColor: colors.border,
            }}
          >
            <Text style={[typography.bodyStrong, { color: colors.text }]}>Scenariusze</Text>
            {[item.conservativeScenario, item.baseScenario].map((scenario) => (
              <View key={scenario.label} style={{ gap: 4 }}>
                <Text style={[typography.bodyStrong, { color: colors.accent }]}>
                  {scenario.label}
                </Text>
                <Text style={[typography.caption, { color: colors.textMuted }]}>
                  Cena negocjowana w scenariuszu bazowym jest hipotetyczna — nie obiecuje rabatu.
                </Text>
                <MoneyValue label="Zakup" amountMinor={scenario.purchaseMinor} />
                <MoneyValue label="Odsprzedaż" amountMinor={scenario.resaleMinor} />
                <MoneyValue label="Zysk operacyjny" amountMinor={scenario.profitMinor} />
              </View>
            ))}
          </View>
        ) : null}

        {item.priceHistory.length > 1 ? (
          <View style={{ gap: spacing.sm }}>
            <Text style={[typography.bodyStrong, { color: colors.text }]}>Historia ceny</Text>
            {item.priceHistory.map((point: { at: string; priceMinor: number | null }) => (
              <Text key={point.at} style={[typography.caption, { color: colors.textMuted }]}>
                {formatUserDateTime(point.at)} —{' '}
                {point.priceMinor !== null ? `${(point.priceMinor / 100).toFixed(2)} zł` : '—'}
              </Text>
            ))}
          </View>
        ) : null}

        <View style={{ gap: spacing.sm }}>
          <PrimaryButton label="Obserwuj" variant="secondary" onPress={() => watchMutation.mutate()} />
          <PrimaryButton
            label="Otwórz ogłoszenie"
            variant="secondary"
            onPress={() => {
              if (!item.url) return;
              Linking.openURL(item.url).catch(() => undefined);
            }}
          />
          {item.listingId ? (
          <PrimaryButton
            label="Dodaj do moich flipów (zakup)"
            onPress={() =>
              router.push({
                pathname: '/purchase/[listingId]',
                params: { listingId: String(item.listingId ?? id) },
              })
            }
          />
          ) : null}
          <PrimaryButton
            label="Analizuj ponownie"
            onPress={() => router.push('/analyze')}
          />
        </View>
      </ScrollView>
    </AppScreen>
  );
}
