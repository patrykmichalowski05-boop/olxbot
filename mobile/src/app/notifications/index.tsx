import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';
import { useInfiniteQuery } from '@tanstack/react-query';
import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { NotificationCard } from '@/components/NotificationCard';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useTheme } from '@/theme/ThemeProvider';
import { workspaceId } from '@/utils/config';

export default function NotificationsScreen() {
  const { colors, typography } = useTheme();
  const [category, setCategory] = useState('ALL');
  const notifications = useInfiniteQuery({
    queryKey: ['notifications', api.mode, workspaceId()], initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => api.notificationsPage(pageParam), getNextPageParam: last => last.nextBeforeId,
  });
  const all = [...new Map((notifications.data?.pages.flatMap(page => page.items) ?? []).map(item => [item.id, item])).values()];
  const categories = ['ALL', ...new Set(all.map(item => item.category))];
  const items = all.filter(item => category === 'ALL' || item.category === category);
  return <AppScreen maxWidth={1200}>
    <Header title="Powiadomienia" subtitle="Zmiany cen i zdarzenia Twoich flipów" showBack showNotifications={false} />
    <DemoBanner />
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
      {categories.map(value => <Pressable key={value} accessibilityRole="button" accessibilityState={{ selected: category === value }} onPress={() => setCategory(value)}
        style={{ minHeight: 40, justifyContent: 'center', paddingHorizontal: 14, borderRadius: 10, backgroundColor: category === value ? colors.accentMuted : colors.surface }}>
        <Text style={[typography.caption, { color: category === value ? colors.accent : colors.textMuted }]}>{value === 'ALL' ? 'Wszystkie' : value}</Text>
      </Pressable>)}
    </View>
    {notifications.isSuccess ? <Text style={[typography.caption, { color: colors.textMuted, marginBottom: 16 }]}>{all.length} pobranych zdarzeń · bez informacji o stanie odczytu</Text> : null}
    {notifications.isPending ? <LoadingSkeleton rows={3} /> : notifications.isError ? <ErrorState message={apiErrorMessage(notifications.error)} onRetry={() => void notifications.refetch()} /> :
      <FlatList data={items} keyExtractor={item => item.id} contentContainerStyle={{ gap: 12, paddingBottom: 16 }}
        refreshControl={<RefreshControl tintColor={colors.accent} refreshing={notifications.isRefetching} onRefresh={() => void notifications.refetch()} />}
        onEndReached={() => { if (notifications.hasNextPage && !notifications.isFetchingNextPage) void notifications.fetchNextPage(); }}
        onEndReachedThreshold={0.4}
        ListFooterComponent={notifications.isFetchingNextPage ? <LoadingSkeleton rows={1} /> : notifications.hasNextPage ? <PrimaryButton label="Wczytaj kolejne zdarzenia" variant="secondary" onPress={() => void notifications.fetchNextPage()} /> : null}
        ListEmptyComponent={<EmptyState title="Brak powiadomień" description="Zdarzenia pojawią się tutaj po ich zapisaniu." />}
        renderItem={({ item }) => <NotificationCard item={item} />} />}
  </AppScreen>;
}
