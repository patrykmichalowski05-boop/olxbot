import React from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { MoneyValue } from '@/components/MoneyValue';
import { useTheme } from '@/theme/ThemeProvider';
import { formatRelativeSync } from '@/utils/datetime';

export default function WatchedScreen() {
  const queryClient = useQueryClient();
  const { colors, spacing, typography, radii } = useTheme();

  const watchQuery = useQuery({
    queryKey: ['watchlist', api.mode],
    queryFn: () => api.watchlist.list(),
  });

  const removeMutation = useMutation({
    mutationFn: (key: string) => api.watchlist.remove(key),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  return (
    <AppScreen padded={false}>
      <View style={{ paddingHorizontal: spacing.lg }}>
        <Header title="Obserwowane" showNotifications />
        <DemoBanner />
      </View>

      {watchQuery.isLoading ? (
        <View style={{ padding: spacing.lg }}>
          <LoadingSkeleton />
        </View>
      ) : watchQuery.isError ? (
        <ErrorState
          message={apiErrorMessage(watchQuery.error)}
          onRetry={() => watchQuery.refetch()}
        />
      ) : (
        <FlatList
          data={watchQuery.data ?? []}
          keyExtractor={(item) => item.listing_key}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
          refreshControl={
            <RefreshControl
              refreshing={watchQuery.isRefetching}
              onRefresh={() => watchQuery.refetch()}
            />
          }
          ListEmptyComponent={
            <EmptyState
              title="Pusta watchlista"
              description="Zapisuj okazje z radaru, aby śledzić cenę i progi."
            />
          }
          renderItem={({ item }) => (
            <View
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
              <Text style={[typography.bodyStrong, { color: colors.text }]}>{item.label}</Text>
              <MoneyValue label="Aktualna cena" amountMinor={item.price_minor ?? null} />
              <MoneyValue label="Próg zakupu" amountMinor={item.threshold_minor ?? null} />
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                Sprawdzone: {formatRelativeSync(item.updated)}
              </Text>
              <Pressable onPress={() => removeMutation.mutate(item.listing_key)}>
                <Text style={[typography.bodyStrong, { color: colors.loss }]}>Usuń</Text>
              </Pressable>
            </View>
          )}
        />
      )}
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1 },
});
