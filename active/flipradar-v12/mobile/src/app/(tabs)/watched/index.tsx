import { RuntimeFeature } from "@/features/runtime/RuntimeFeature";
import React, { useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import { AppScreen } from "@/components/AppScreen";
import { Badge } from "@/components/Badge";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Header } from "@/components/Header";
import { IconButton } from "@/components/IconButton";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { MoneyValue } from "@/components/MoneyValue";
import { useTheme } from "@/theme/ThemeProvider";
import { formatRelativeSync } from "@/utils/datetime";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { savedOfferId } from "@/features/workspace/presentation";
import { PrimaryButton } from "@/components/PrimaryButton";
import { useAuth } from "@/features/auth/AuthContext";

function WatchedScreenContent() {
  const router = useRouter();
  const { pagePadding } = useWorkspaceLayout();
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const { colors, spacing, typography, radii } = useTheme();
  const [removeError, setRemoveError] = useState("");
  const watchQuery = useQuery({
    queryKey: ["watchlist", api.mode, userId],
    queryFn: () => api.watchlist.list(),
  });
  const removeMutation = useMutation({
    mutationFn: (key: string) => api.watchlist.remove(key),
    onSuccess: () => {
      setRemoveError("");
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
    onError: (error) => setRemoveError(apiErrorMessage(error)),
  });
  const items = watchQuery.data ?? [];
  return (
    <AppScreen padded={false} bottomInset={false}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.listing_key}
        contentContainerStyle={{
          paddingHorizontal: pagePadding,
          paddingBottom: spacing.lg,
          gap: spacing.md,
          flexGrow: 1,
        }}
        refreshControl={
          <RefreshControl
            refreshing={watchQuery.isRefetching}
            onRefresh={() => {
              void watchQuery.refetch();
            }}
            tintColor={colors.accent}
            colors={[colors.accent]}
          />
        }
        ListHeaderComponent={
          <View style={{ gap: spacing.md, marginBottom: spacing.sm }}>
            <Header
              title="Zapisane okazje"
              subtitle="Wszystko, co chcesz mieć na oku."
            />
            <DemoBanner />
            {watchQuery.data ? (
              <View style={styles.row}>
                <Badge
                  label={`${items.length} zapisanych`}
                  tone="accent"
                  icon="bookmark-outline"
                />
                <Text style={[typography.caption, { color: colors.textMuted }]}>
                  Twoja watchlista
                </Text>
              </View>
            ) : null}
            {watchQuery.isRefetchError && watchQuery.data ? (
              <ErrorState
                message="Nie udało się odświeżyć zapisanych ofert. Widzisz ostatnio pobrane dane."
                onRetry={() => {
                  void watchQuery.refetch();
                }}
                retrying={watchQuery.isFetching}
              />
            ) : null}
            {removeError ? (
              <ErrorState
                title="Nie udało się usunąć oferty"
                message={removeError}
                onRetry={() => {
                  if (removeMutation.variables)
                    removeMutation.mutate(removeMutation.variables);
                }}
                retrying={removeMutation.isPending}
              />
            ) : null}
          </View>
        }
        ListEmptyComponent={
          watchQuery.isError &&
          watchQuery.data ? null : watchQuery.isPending ? (
            <LoadingSkeleton />
          ) : watchQuery.isError ? (
            <ErrorState
              title="Zapisane oferty są chwilowo niedostępne"
              message={apiErrorMessage(watchQuery.error)}
              onRetry={() => {
                void watchQuery.refetch();
              }}
              retrying={watchQuery.isFetching}
            />
          ) : (
            <EmptyState
              icon="bookmark-outline"
              title="Twoja lista czeka na pierwszą okazję"
              description="Zapisz ofertę w radarze. Tutaj wrócisz do niej, porównasz cenę i podejmiesz decyzję."
              actionLabel="Przejdź do radaru"
              onAction={() => router.push("/radar")}
            />
          )
        }
        renderItem={({ item }) => {
          const detailId = savedOfferId(item.listing_key, api.mode === "demo");
          const underThreshold =
            item.price_minor != null &&
            item.threshold_minor != null &&
            item.price_minor <= item.threshold_minor;
          return (
            <View
              style={[
                styles.card,
                {
                  backgroundColor: colors.surface,
                  borderColor: underThreshold
                    ? colors.accentMuted
                    : colors.border,
                  borderRadius: radii.xxl,
                  padding: spacing.lg,
                  gap: spacing.lg,
                },
              ]}
            >
              <View style={styles.top}>
                <View
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: radii.md,
                    backgroundColor: colors.accentBg,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Ionicons name="bookmark" size={20} color={colors.accent} />
                </View>
                <Text
                  style={[
                    typography.bodyStrong,
                    { flex: 1, color: colors.text },
                  ]}
                  numberOfLines={2}
                >
                  {item.label || "Zapisana oferta"}
                </Text>
                <IconButton
                  icon="trash-outline"
                  label={`Usuń z zapisanych: ${item.label}`}
                  onPress={() => removeMutation.mutate(item.listing_key)}
                  disabled={removeMutation.isPending}
                  loading={
                    removeMutation.isPending &&
                    removeMutation.variables === item.listing_key
                  }
                />
              </View>
              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  gap: spacing.xl,
                }}
              >
                <MoneyValue
                  label="Aktualna cena"
                  amountMinor={item.price_minor}
                  emptyLabel="Brak ceny"
                />
                <MoneyValue
                  label="Próg zakupu"
                  amountMinor={item.threshold_minor}
                  emptyLabel="Nie ustawiono"
                />
              </View>
              {underThreshold ? (
                <Badge
                  label="Cena w Twoim budżecie"
                  tone="success"
                  icon="trending-down-outline"
                />
              ) : null}
              <Text style={[typography.caption, { color: colors.textSubtle }]}>
                Ostatnie sprawdzenie: {formatRelativeSync(item.updated)}
              </Text>
              {detailId ? (
                <PrimaryButton
                  label="Zobacz szczegóły"
                  variant="secondary"
                  onPress={() =>
                    router.push({
                      pathname: "/offer/[id]",
                      params: { id: detailId },
                    })
                  }
                />
              ) : null}
            </View>
          );
        }}
      />
    </AppScreen>
  );
}
const styles = StyleSheet.create({
  card: { borderWidth: 1 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  top: { flexDirection: "row", alignItems: "center", gap: 12 },
});

export default function WatchedScreen() {
  return (
    <RuntimeFeature
      feature="watchlist"
      title="Zapisane oferty"
      description="Zapisywanie pojedynczych ofert nie jest jeszcze dostępne w tym panelu. Możesz wrócić do radaru lub otworzyć centrum narzędzi."
      icon="bookmark-outline"
    >
      <WatchedScreenContent />
    </RuntimeFeature>
  );
}
