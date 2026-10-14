import React from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
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
import { useTheme } from '@/theme/ThemeProvider';
import { workspaceId } from '@/utils/config';

export default function FlipsScreen() {
  const router = useRouter();
  const { colors, spacing, typography, radii } = useTheme();
  const ws = workspaceId();

  const dealsQuery = useQuery({
    queryKey: ['deals', api.mode],
    queryFn: () => api.deals.list(),
  });

  return (
    <AppScreen padded={false}>
      <View style={{ paddingHorizontal: spacing.lg, gap: spacing.sm }}>
        <Header title="Moje flipy" />
        <DemoBanner />
        <PrimaryButton
          label="Analityka"
          variant="secondary"
          onPress={() => router.push('/analytics')}
        />
        {api.mode === 'live' && !ws ? (
          <Text style={[typography.caption, { color: colors.risk }]}>
            Ustaw EXPO_PUBLIC_FLIP_WORKSPACE_ID, aby zapisywać zakupy przez API v2.
          </Text>
        ) : null}
      </View>

      {dealsQuery.isLoading ? (
        <View style={{ padding: spacing.lg }}>
          <LoadingSkeleton />
        </View>
      ) : dealsQuery.isError ? (
        <ErrorState
          message={apiErrorMessage(dealsQuery.error)}
          onRetry={() => dealsQuery.refetch()}
        />
      ) : (
        <FlatList
          data={dealsQuery.data?.items ?? []}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
          refreshControl={
            <RefreshControl
              refreshing={dealsQuery.isRefetching}
              onRefresh={() => dealsQuery.refetch()}
            />
          }
          ListEmptyComponent={
            <EmptyState
              title="Brak flipów"
              description="Dodaj zakup z ekranu szczegółów oferty."
            />
          }
          renderItem={({ item }) => (
            <Pressable
              onPress={() =>
                router.push({
                  pathname: '/flips/[dealId]',
                  params: { dealId: item.id },
                })
              }
              style={[
                styles.card,
                {
                  backgroundColor: colors.surface,
                  borderColor: colors.border,
                  borderRadius: radii.md,
                  padding: spacing.md,
                  gap: spacing.sm,
                },
              ]}
            >
              <Text style={[typography.bodyStrong, { color: colors.text }]}>
                {item.title ?? item.id}
              </Text>
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                Status: {item.status ?? '—'}
              </Text>
              <View style={styles.row}>
                <MoneyValue label="Zakup" amountMinor={item.purchase_minor ?? null} />
                <MoneyValue label="Koszty" amountMinor={item.cost_minor ?? null} />
                <MoneyValue label="Wynik" amountMinor={item.realized_profit_minor ?? null} />
              </View>
            </Pressable>
          )}
        />
      )}
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
});
