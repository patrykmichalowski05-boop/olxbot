import React, { useEffect, useMemo, useState } from "react";
import {
  FlatList,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import { AppScreen } from "@/components/AppScreen";
import { Badge } from "@/components/Badge";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FilterSheet } from "@/components/FilterSheet";
import { Header } from "@/components/Header";
import { IconButton } from "@/components/IconButton";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PrimaryButton } from "@/components/PrimaryButton";
import type { OpportunityCard } from "@/features/opportunity/types";
import { radarSummary } from "@/features/opportunity/presentation";
import {
  applyClientFilters,
  countActiveFilters,
  defaultFilters,
  loadFilters,
  loadProfiles,
  saveFilters,
  saveProfiles,
  type RadarFilters,
  type SavedFilterProfile,
} from "@/features/radar/filterStore";
import { useRadarOffers, useWatchActions } from "@/features/workspace/hooks";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { OfferRow } from "@/features/workspace/OfferRow";
import { RadarToolbar } from "@/features/workspace/RadarToolbar";
import { WorkspaceNotice } from "@/features/workspace/WorkspaceNotice";
import { priceLabel, safeOfferUrl } from "@/features/workspace/presentation";
import { useRuntimeCapabilities } from "@/features/runtime/useRuntimeCapabilities";
import { useTheme } from "@/theme/ThemeProvider";
import { radarSource } from "@/utils/config";
import { CATEGORY_TABS } from "@/utils/labels";
import { formatRoiBps } from "@/utils/money";

export default function RadarScreen() {
  const router = useRouter();
  const runtime = useRuntimeCapabilities();
  const { colors, typography, radii } = useTheme();
  const { pagePadding } = useWorkspaceLayout();
  const [filters, setFilters] = useState<RadarFilters>(defaultFilters);
  const [filtersReady, setFiltersReady] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [profiles, setProfiles] = useState<SavedFilterProfile[]>([]);
  const [notice, setNotice] = useState("");
  const { request, items: loaded } = useRadarOffers(
    filters.query,
    filtersReady,
    filters,
  );
  const watch = useWatchActions();

  useEffect(() => {
    let alive = true;
    void loadFilters().then((value) => {
      if (alive) {
        setFilters(value);
        setFiltersReady(true);
      }
    });
    void loadProfiles().then((value) => {
      if (alive) setProfiles(value);
    });
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    if (!filtersReady) return;
    const timer = setTimeout(() => {
      void saveFilters(filters).catch(() =>
        setNotice("Nie udało się zapamiętać filtrów na tym urządzeniu."),
      );
    }, 300);
    return () => clearTimeout(timer);
  }, [filters, filtersReady]);
  const items = useMemo(
    () => applyClientFilters(loaded, filters),
    [loaded, filters],
  );
  const stats = useMemo(() => radarSummary(items), [items]);
  const filterCount = countActiveFilters(filters);
  const openOffer = (item: OpportunityCard) => {
    if (api.mode === "live" && radarSource() === "legacy" && !item.listingId) {
      const url = safeOfferUrl(item.platform, item.url);
      if (url)
        void Linking.openURL(url).catch(() =>
          setNotice("Nie udało się otworzyć ogłoszenia. Spróbuj ponownie."),
        );
      else setNotice("To ogłoszenie nie ma dostępnego linku.");
      return;
    }
    router.push({
      pathname: "/offer/[id]",
      params: { id: item.listingId ? String(item.listingId) : item.id },
    });
  };
  const header = (
    <View style={{ gap: 20, marginBottom: 12 }}>
      <RadarToolbar
        key={JSON.stringify(filters)}
        value={filters}
        onApply={setFilters}
        onClear={() => setFilters(defaultFilters)}
      />
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 6 }}
          style={{ flexGrow: 1 }}
        >
          {CATEGORY_TABS.map((tab) => (
            <Pressable
              key={tab.id}
              accessibilityRole="button"
              accessibilityState={{ selected: filters.category === tab.id }}
              onPress={() =>
                setFilters((old) => ({ ...old, category: tab.id }))
              }
              style={{
                minHeight: 36,
                paddingVertical: 8,
                paddingHorizontal: 12,
                borderRadius: 20,
                borderWidth: 1,
                borderColor:
                  filters.category === tab.id
                    ? colors.accentMuted
                    : colors.border,
                backgroundColor:
                  filters.category === tab.id
                    ? colors.accentBg
                    : colors.surface,
              }}
            >
              <Text
                style={[
                  typography.caption,
                  {
                    color:
                      filters.category === tab.id
                        ? colors.accent
                        : colors.textMuted,
                    fontWeight: "600",
                  },
                ]}
              >
                {tab.label}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
        <PrimaryButton
          label={`Dodatkowe filtry${filterCount ? ` · ${filterCount}` : ""}`}
          variant="ghost"
          icon="options-outline"
          onPress={() => setFiltersOpen(true)}
        />
      </View>
      <DemoBanner />
      {profiles.length ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 8 }}
        >
          {profiles.map((profile) => (
            <PrimaryButton
              key={profile.id}
              label={profile.name}
              variant="secondary"
              onPress={() =>
                setFilters({ ...defaultFilters, ...profile.filters })
              }
            />
          ))}
        </ScrollView>
      ) : null}
      {request.data ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 16 }}>
          {[
            ["Oferty", String(stats.count)],
            ["Średni ROI", formatRoiBps(stats.averageRoiBps)],
            ["Hot deals", String(stats.hotCount)],
            ["Potencjalny wynik", priceLabel(stats.potentialMinor)],
          ].map(([label, value]) => (
            <Text
              key={label}
              style={[typography.caption, { color: colors.textMuted }]}
            >
              {label}:{" "}
              <Text style={{ fontWeight: "700", color: colors.text }}>
                {value}
              </Text>
            </Text>
          ))}
        </View>
      ) : null}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Text
          accessibilityRole="header"
          style={[typography.bodyStrong, { fontSize: 16, color: colors.text }]}
        >
          {request.data
            ? `Znaleziono ${items.length} ofert${request.hasNextPage ? " w wczytanych wynikach" : ""}`
            : "Twoje oferty"}
        </Text>
        <Badge
          label={api.mode === "demo" ? "Oceny przykładowe" : "Twój radar"}
          tone="accent"
        />
      </View>
      {request.data ? (
        <Text style={[typography.caption, { color: colors.textSubtle }]}>
          Podsumowanie i filtry dotyczą wczytanych ofert. Potencjalny wynik to
          suma dodatnich prognoz przed podatkiem.
        </Text>
      ) : null}
      {notice || watch.notice ? (
        <WorkspaceNotice
          text={notice || watch.notice}
          onDismiss={() => {
            setNotice("");
            watch.clearNotice();
          }}
        />
      ) : null}
      {request.isRefetchError && request.data ? (
        <ErrorState
          message="Nie udało się odświeżyć listy. Widzisz ostatnio pobrane oferty."
          onRetry={() => {
            void request.refetch();
          }}
          retrying={request.isFetching}
        />
      ) : null}
      {watch.saved.isError ? (
        <ErrorState
          title="Zapisane oferty są chwilowo niedostępne"
          message="Możesz przeglądać radar. Ponów odczyt zapisanych, aby obserwować kolejne oferty."
          onRetry={() => {
            void watch.saved.refetch();
          }}
        />
      ) : null}
    </View>
  );

  return (
    <AppScreen padded={false} bottomInset={false}>
      <View style={{ paddingHorizontal: pagePadding }}>
        <Header
          title="Flip Radar"
          subtitle={
            runtime.capabilities.radar_scope === "global"
              ? "Radar administratora · wszystkie zebrane oferty"
              : "Radar okazji — oferty z Twoich wyszukiwań"
          }
          rightSlot={
            <IconButton
              label="Odśwież radar"
              icon="refresh-outline"
              loading={request.isRefetching}
              onPress={() => {
                void request.refetch();
              }}
            />
          }
        />
      </View>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        contentContainerStyle={{
          paddingHorizontal: pagePadding,
          paddingBottom: 28,
          flexGrow: 1,
        }}
        ListHeaderComponent={header}
        refreshControl={
          <RefreshControl
            refreshing={request.isRefetching && !request.isFetchingNextPage}
            onRefresh={() => {
              void request.refetch();
            }}
            tintColor={colors.accent}
            colors={[colors.accent]}
          />
        }
        ListEmptyComponent={
          request.isPending || !filtersReady ? (
            <LoadingSkeleton rows={4} compact />
          ) : request.isError ? (
            <ErrorState
              message={apiErrorMessage(request.error)}
              onRetry={() => {
                void request.refetch();
              }}
              retrying={request.isFetching}
            />
          ) : (
            <EmptyState
              title={
                loaded.length
                  ? "Brak ofert w wybranym zakresie"
                  : "Radar czeka na Twoje okazje"
              }
              icon="search-outline"
              description={
                loaded.length
                  ? "Zmień zakres cen, platformę lub kategorię. Kolejne strony mogą zawierać dodatkowe wyniki."
                  : "Zapisz model w „Moje wyszukiwania”. Oferty pojawią się po sprawdzeniu podłączonych źródeł."
              }
              actionLabel={
                filterCount || filters.query
                  ? "Wyczyść filtry"
                  : "Dodaj wyszukiwanie"
              }
              onAction={() =>
                filterCount || filters.query
                  ? setFilters(defaultFilters)
                  : router.push("/searches")
              }
            />
          )
        }
        renderItem={({ item, index }) => (
          <View
            style={{
              borderLeftWidth: 1,
              borderRightWidth: 1,
              borderTopWidth: index === 0 ? 1 : 0,
              borderBottomWidth: index === items.length - 1 ? 1 : 0,
              borderColor: colors.border,
              borderTopLeftRadius: index === 0 ? radii.xl : 0,
              borderTopRightRadius: index === 0 ? radii.xl : 0,
              borderBottomLeftRadius: index === items.length - 1 ? radii.xl : 0,
              borderBottomRightRadius:
                index === items.length - 1 ? radii.xl : 0,
              overflow: "hidden",
            }}
          >
            <OfferRow
              item={item}
              last={index === items.length - 1}
              onPress={() => openOffer(item)}
              onWatch={watch.available ? () => watch.toggle(item) : undefined}
              watched={watch.isWatched(item)}
              watchLoading={
                watch.mutation.isPending &&
                watch.mutation.variables?.item.id === item.id
              }
              watchDisabled={
                !watch.writable ||
                watch.mutation.isPending ||
                watch.saved.isError ||
                watch.saved.isPending
              }
            />
          </View>
        )}
        ListFooterComponent={
          <View style={{ marginTop: 20, gap: 12 }}>
            {request.isFetchNextPageError ? (
              <ErrorState
                message="Nie udało się pobrać kolejnych ofert."
                onRetry={() => {
                  void request.fetchNextPage();
                }}
              />
            ) : request.hasNextPage ? (
              <PrimaryButton
                label="Wczytaj więcej ofert"
                loading={request.isFetchingNextPage}
                variant="secondary"
                onPress={() => {
                  void request.fetchNextPage();
                }}
              />
            ) : null}
          </View>
        }
      />
      <FilterSheet
        visible={filtersOpen}
        initial={filters}
        onClose={() => setFiltersOpen(false)}
        onApply={(next) => {
          setFilters(next);
          setFiltersOpen(false);
        }}
        onSaveProfile={async (name, next) => {
          const updated = [
            { id: `${Date.now()}`, name, filters: next },
            ...profiles.filter((profile) => profile.name !== name),
          ];
          try {
            await saveProfiles(updated);
            setProfiles(updated);
            setNotice("Profil filtrów zapisany na tym urządzeniu.");
          } catch {
            setNotice("Nie udało się zapisać filtrów. Spróbuj ponownie.");
          }
        }}
      />
    </AppScreen>
  );
}
