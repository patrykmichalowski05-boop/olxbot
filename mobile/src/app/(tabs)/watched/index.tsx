import React from 'react';
import { FlatList, RefreshControl, Text, View } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { WatchedCard } from '@/components/WatchedCard';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';

export default function WatchedScreen() {
  const queryClient = useQueryClient();
  const { colors, typography } = useTheme();
  const { columns, contentWidth } = useResponsiveLayout();
  const watchQuery = useQuery({ queryKey: ['watchlist', api.mode], queryFn: () => api.watchlist.list() });
  const remove = useMutation({ mutationFn: (key: string) => api.watchlist.remove(key), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }) });
  return <AppScreen>
    <Header title="Obserwowane" subtitle="Zapisane produkty, ceny i progi zakupu" />
    <DemoBanner />
    {remove.isError ? <Text accessibilityRole="alert" style={[typography.caption, { color: colors.loss, marginBottom: 12 }]}>{apiErrorMessage(remove.error)}</Text> : null}
    {watchQuery.isPending ? <LoadingSkeleton /> : watchQuery.isError ? <ErrorState message={apiErrorMessage(watchQuery.error)} onRetry={() => void watchQuery.refetch()} /> :
      <FlatList key={columns} data={watchQuery.data} numColumns={columns} keyExtractor={item => item.listing_key}
        columnWrapperStyle={columns > 1 ? { gap: 16 } : undefined} contentContainerStyle={{ gap: 16, paddingBottom: 16 }}
        refreshControl={<RefreshControl tintColor={colors.accent} refreshing={watchQuery.isRefetching} onRefresh={() => void watchQuery.refetch()} />}
        ListEmptyComponent={<EmptyState title="Brak obserwowanych" description="Zapisuj okazje z radaru, aby śledzić cenę i progi." />}
        renderItem={({ item }) => <View style={{ width: (contentWidth - (columns - 1) * 16) / columns }}>
          <WatchedCard item={item} onRemove={() => remove.mutate(item.listing_key)} pending={remove.isPending && remove.variables === item.listing_key} />
        </View>} />}
  </AppScreen>;
}
