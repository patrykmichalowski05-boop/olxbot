import React from "react";
import { FlatList, RefreshControl, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { getSearches, getSourceHealth } from "@/api/endpoints/searches";
import { apiErrorMessage } from "@/api/errors";
import { AccountAccessBoundary } from "@/features/portal/AccountAccessBoundary";
import { AppScreen } from "@/components/AppScreen";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Header } from "@/components/Header";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PrimaryButton } from "@/components/PrimaryButton";
import { useAuth } from "@/features/auth/AuthContext";
import { demoSearches } from "@/features/workspace/demoSearches";
import { useRadarOffers, useWatchActions } from "@/features/workspace/hooks";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { MarketSummary } from "@/features/workspace/MarketSummary";
import { OfferAnalysisCard } from "@/features/workspace/OfferAnalysisCard";
import { platformName } from "@/features/workspace/presentation";
import { filterSearchResults } from "@/features/workspace/searchResults";
import { WorkspaceNotice } from "@/features/workspace/WorkspaceNotice";
import { useTheme } from "@/theme/ThemeProvider";
import { radarSource } from "@/utils/config";

function SearchResultsContent() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { userId, mode, ready, signedIn } = useAuth();
  const { pagePadding } = useWorkspaceLayout();
  const { colors, typography } = useTheme();
  const router = useRouter();
  const profiles = useQuery({
    queryKey: ["saved-searches", userId, mode],
    queryFn: ({ signal }) =>
      mode === "demo" ? demoSearches.list() : getSearches(signal),
    enabled: ready && signedIn,
  });
  const profile = profiles.data?.find((item) => item.id === id);
  const { items: loadedItems, request } = useRadarOffers(
    profile?.query ?? "",
    Boolean(profile),
  );
  const items = filterSearchResults(loadedItems, profile);
  const health = useQuery({
    queryKey: ["source-health", userId],
    queryFn: ({ signal }) => getSourceHealth(signal),
    enabled: ready && signedIn && mode === "live",
  });
  const watch = useWatchActions();
  const scanAt = health.data?.items
    .filter(
      (row) =>
        row.search_id === profile?.id &&
        Number.isFinite(Date.parse(row.checked_at)),
    )
    .map((row) => row.checked_at)
    .sort((a, b) => Date.parse(b) - Date.parse(a))[0];
  const period =
    typeof profile?.reference_days === "number" &&
    Number.isSafeInteger(profile.reference_days) &&
    profile.reference_days > 0
      ? profile.reference_days
      : null;
  const platforms = [...new Set(items.map((item) => item.platform))];
  const canRead = Boolean(profile) && profiles.isSuccess;
  return (
    <AppScreen padded={false} bottomInset={false}>
      <View style={{ paddingHorizontal: pagePadding }}>
        <Header
          title={`Wyniki: ${profile?.name ?? "Twoje wyszukiwanie"}`}
          showBack
          backLabel="Moje wyszukiwania"
          onBack={() => router.navigate("/searches")}
        />
      </View>
      {profiles.isError ? (
        <View style={{ paddingHorizontal: pagePadding }}>
          <ErrorState
            message={apiErrorMessage(profiles.error)}
            onRetry={() => {
              void profiles.refetch();
            }}
          />
        </View>
      ) : profiles.isPending ? (
        <View style={{ paddingHorizontal: pagePadding }}>
          <LoadingSkeleton rows={2} />
        </View>
      ) : !profile ? (
        <View style={{ paddingHorizontal: pagePadding }}>
          <EmptyState
            title="Nie znaleziono wyszukiwania"
            description="Wybierz zapisany model z listy na swoim koncie."
            actionLabel="Moje wyszukiwania"
            onAction={() => router.replace("/searches")}
          />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{
            paddingHorizontal: pagePadding,
            paddingBottom: 28,
            gap: 16,
            flexGrow: 1,
          }}
          refreshControl={
            <RefreshControl
              refreshing={request.isRefetching && !request.isFetchingNextPage}
              onRefresh={() => {
                void profiles.refetch();
                void request.refetch();
                if (mode === "live") void health.refetch();
              }}
              tintColor={colors.accent}
              colors={[colors.accent]}
            />
          }
          ListHeaderComponent={
            <View style={{ gap: 20 }}>
              <DemoBanner />
              <MarketSummary
                items={items}
                title={`Analiza cen${platforms.length === 1 ? ` ${platformName(platforms[0])}` : ""}`}
                periodDays={period}
                scanAt={scanAt}
                loading={!request.data}
              />
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                Oferty z Twojego radaru pasujące do frazy „{profile.query}”,
                platform i budżetu profilu. Porównanie konkretnego wariantu
                znajduje się na karcie oferty.
              </Text>
              {!profile.enabled ? (
                <WorkspaceNotice text="To wyszukiwanie jest wstrzymane. Włącz je na liście, aby otrzymywać nowe oferty." />
              ) : null}
              {health.data?.items.some(
                (row) => row.search_id === profile.id && row.status !== "OK",
              ) ? (
                <WorkspaceNotice text="Część źródeł czeka na ponowne sprawdzenie. Lista może być niepełna." />
              ) : null}
              {health.isError ? (
                <ErrorState
                  title="Stan źródeł chwilowo niedostępny"
                  message="Możesz przeglądać oferty. Spróbuj ponownie pobrać informacje o ostatnim skanie."
                  onRetry={() => {
                    void health.refetch();
                  }}
                  retrying={health.isFetching}
                />
              ) : null}
              {watch.saved.isError ? (
                <ErrorState
                  title="Zapisywanie ofert chwilowo niedostępne"
                  message="Spróbuj ponownie pobrać listę zapisanych ofert."
                  onRetry={() => {
                    void watch.saved.refetch();
                  }}
                  retrying={watch.saved.isFetching}
                />
              ) : null}
              {watch.notice ? (
                <WorkspaceNotice
                  text={watch.notice}
                  onDismiss={watch.clearNotice}
                />
              ) : null}
              {request.isRefetchError && request.data ? (
                <ErrorState
                  message="Nie udało się odświeżyć wyników. Widzisz ostatnio pobrane dane."
                  onRetry={() => {
                    void request.refetch();
                  }}
                />
              ) : null}
              <Text
                accessibilityRole="header"
                style={[typography.headline, { color: colors.text }]}
              >
                Oferty ({request.data ? items.length : "—"})
                {request.hasNextPage ? " · wczytane" : ""}
              </Text>
            </View>
          }
          ListEmptyComponent={
            !canRead || request.isPending ? (
              <LoadingSkeleton rows={2} />
            ) : request.isError ? (
              <ErrorState
                message={apiErrorMessage(request.error)}
                onRetry={() => {
                  void request.refetch();
                }}
              />
            ) : (
              <EmptyState
                icon="search-outline"
                title="Brak ofert dla tego wyszukiwania"
                description="Sprawdź, czy profil jest aktywny. Wyniki pojawią się po udanym skanie skonfigurowanych źródeł."
                actionLabel="Moje wyszukiwania"
                onAction={() => router.navigate("/searches")}
              />
            )
          }
          renderItem={({ item, index }) => (
            <OfferAnalysisCard
              item={item}
              demo={mode === "demo"}
              defaultExpanded={index === 0}
              onDetails={
                mode === "demo" ||
                radarSource() === "universal" ||
                item.listingId
                  ? () =>
                      router.push({
                        pathname: "/offer/[id]",
                        params: {
                          id: item.listingId ? String(item.listingId) : item.id,
                        },
                      })
                  : undefined
              }
              onWatch={() => watch.toggle(item)}
              watched={watch.isWatched(item)}
              watchLoading={
                watch.mutation.isPending &&
                watch.mutation.variables?.item.id === item.id
              }
              watchDisabled={
                watch.mutation.isPending ||
                watch.saved.isPending ||
                watch.saved.isError
              }
            />
          )}
          ListFooterComponent={
            request.isFetchNextPageError ? (
              <ErrorState
                message="Nie udało się pobrać kolejnej strony."
                onRetry={() => {
                  void request.fetchNextPage();
                }}
              />
            ) : request.hasNextPage ? (
              <PrimaryButton
                label="Wczytaj więcej ofert"
                variant="secondary"
                loading={request.isFetchingNextPage}
                onPress={() => {
                  void request.fetchNextPage();
                }}
              />
            ) : null
          }
        />
      )}
    </AppScreen>
  );
}

export default function SearchResultsScreen() {
  return (
    <AccountAccessBoundary>
      <SearchResultsContent />
    </AccountAccessBoundary>
  );
}
