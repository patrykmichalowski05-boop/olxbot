import React from "react";
import { FlatList, RefreshControl, Text, View } from "react-native";
import { useInfiniteQuery } from "@tanstack/react-query";

import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import { AppScreen } from "@/components/AppScreen";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Header } from "@/components/Header";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { useTheme } from "@/theme/ThemeProvider";
import { formatUserDateTime } from "@/utils/datetime";
import { workspaceId } from "@/utils/config";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { useAuth } from "@/features/auth/AuthContext";

export default function NotificationsScreen() {
  const { pagePadding } = useWorkspaceLayout();
  const { userId } = useAuth();
  const { colors, spacing, typography, radii } = useTheme();
  const notifications = useInfiniteQuery({
    queryKey: ["notifications", api.mode, workspaceId(), userId],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => api.notificationsPage(pageParam),
    getNextPageParam: (lastPage) => lastPage.nextBeforeId,
  });
  const items = notifications.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <AppScreen padded={false}>
      <View style={{ paddingHorizontal: pagePadding }}>
        <Header title="Powiadomienia" showBack showNotifications={false} />
        <DemoBanner />
      </View>

      {notifications.isLoading ? (
        <View style={{ padding: pagePadding }}>
          <LoadingSkeleton rows={3} />
        </View>
      ) : notifications.isError ? (
        <ErrorState
          message={apiErrorMessage(notifications.error)}
          onRetry={() => void notifications.refetch()}
        />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{
            paddingHorizontal: pagePadding,
            paddingBottom: pagePadding,
            gap: spacing.md,
          }}
          refreshControl={
            <RefreshControl
              refreshing={notifications.isRefetching}
              onRefresh={() => void notifications.refetch()}
            />
          }
          onEndReached={() => {
            if (
              notifications.hasNextPage &&
              !notifications.isFetchingNextPage
            ) {
              void notifications.fetchNextPage();
            }
          }}
          onEndReachedThreshold={0.4}
          ListFooterComponent={
            notifications.isFetchingNextPage ? (
              <LoadingSkeleton rows={1} />
            ) : null
          }
          ListEmptyComponent={
            <EmptyState
              title="Brak powiadomień"
              description="Zdarzenia z backendu pojawią się tutaj po ich przetworzeniu."
            />
          }
          renderItem={({ item }) => (
            <View
              style={{
                backgroundColor: colors.surface,
                borderRadius: radii.md,
                padding: spacing.md,
                borderWidth: 1,
                borderColor: colors.border,
                gap: spacing.xs,
              }}
            >
              <Text style={[typography.caption, { color: colors.accent }]}>
                {item.category}
              </Text>
              <Text style={[typography.bodyStrong, { color: colors.text }]}>
                {item.title}
              </Text>
              <Text style={[typography.body, { color: colors.textMuted }]}>
                {item.reason}
              </Text>
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                {formatUserDateTime(item.at)}
              </Text>
            </View>
          )}
        />
      )}
    </AppScreen>
  );
}
