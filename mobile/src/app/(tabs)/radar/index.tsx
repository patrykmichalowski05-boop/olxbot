import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FlatList,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { api } from '@/api';
import type { UniversalWatchItem } from '@/api/endpoints/universal';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { FilterSheet } from '@/components/FilterSheet';
import { Header } from '@/components/Header';
import { IconButton } from '@/components/IconButton';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PrimaryButton } from '@/components/PrimaryButton';
import { ProductCard } from '@/components/ProductCard';
import { StatCard } from '@/components/StatCard';
import type { OpportunityCard } from '@/features/opportunity/types';
import { radarSummary } from '@/features/opportunity/presentation';
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
} from '@/features/radar/filterStore';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useTheme } from '@/theme/ThemeProvider';
import { radarSource } from '@/utils/config';
import { CATEGORY_TABS } from '@/utils/labels';
import { formatMoneyMinor, formatRoiBps } from '@/utils/money';

const sortLabels: Record<RadarFilters['sort'], string> = {
  fresh: 'Najnowsze',
  profit: 'Najwyższy wynik',
  roi: 'Najwyższy ROI',
  price: 'Najniższa cena',
  quality: 'Z wyceną',
};

export default function RadarScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { colors, spacing, typography, radii } = useTheme();
  const { width } = useWindowDimensions();
  const columns = width >= 780 ? 2 : 1;
  const [filters, setFilters] = useState<RadarFilters>(defaultFilters);
  const [filtersReady, setFiltersReady] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [profiles, setProfiles] = useState<SavedFilterProfile[]>([]);
  const [notice, setNotice] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const query = useDebouncedValue(filters.query);

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
        setNotice('Nie udało się zapamiętać filtrów na tym urządzeniu.'),
      );
    }, 300);
    return () => clearTimeout(timer);
  }, [filters, filtersReady]);

  const radarQuery = useInfiniteQuery({
    queryKey: ['radar', query, api.mode],
    enabled: filtersReady,
    initialPageParam: null as number | null,
    queryFn: ({ pageParam, signal }) =>
      api.radarPage({ beforeId: pageParam, q: query, signal }),
    getNextPageParam: (last) => last.nextBeforeId,
  });
  const watchQuery = useQuery({
    queryKey: ['watchlist', api.mode],
    queryFn: () => api.watchlist.list(),
  });
  const watchedKeys = useMemo(
    () => new Set(watchQuery.data?.map((item) => item.listing_key)),
    [watchQuery.data],
  );
  const items = useMemo(() => {
    const flat = radarQuery.data?.pages.flatMap((page) => page.items) ?? [];
    const unique = new Map(flat.map((item) => [item.id, item]));
    return applyClientFilters([...unique.values()], filters);
  }, [radarQuery.data, filters]);
  const stats = useMemo(() => radarSummary(items), [items]);
  const statsReady = Boolean(radarQuery.data);
  const activeFilterCount = countActiveFilters(filters);
  const watchMutation = useMutation({
    mutationFn: ({ item, remove }: { item: OpportunityCard; remove: boolean }) =>
      remove ? api.watchlist.remove(item.id) : api.watchlist.add(item.id, item.title),
    onSuccess: (_, { item, remove }) => {
      queryClient.setQueryData<UniversalWatchItem[]>(['watchlist', api.mode], (old) =>
        remove
          ? old?.filter((saved) => saved.listing_key !== item.id)
          : [
              {
                listing_key: item.id,
                label: item.title,
                updated: new Date().toISOString(),
              },
              ...(old ?? []).filter((saved) => saved.listing_key !== item.id),
            ],
      );
      void queryClient.invalidateQueries({ queryKey: ['watchlist'] });
      setNotice(
        remove ? 'Oferta usunięta z zapisanych.' : 'Oferta dodana do zapisanych.',
      );
    },
    onError: (error) => setNotice(apiErrorMessage(error)),
  });
  const onApplyFilters = useCallback((next: RadarFilters) => {
    setFilters(next);
    setFiltersOpen(false);
  }, []);
  const openOffer = (item: OpportunityCard) => {
    if (api.mode === 'live' && radarSource() === 'legacy' && !item.listingId) {
      if (item.url)
        void Linking.openURL(item.url).catch(() =>
          setNotice('Nie udało się otworzyć ogłoszenia. Spróbuj ponownie.'),
        );
      else setNotice('To ogłoszenie nie ma już dostępnego linku.');
      return;
    }
    router.push({
      pathname: '/offer/[id]',
      params: { id: item.listingId ? String(item.listingId) : item.id },
    });
  };
  const header = (
    <View style={{ gap: spacing.md }}>
      <View>
        <Header
          title="Radar okazji"
          subtitle="Wyszukuj. Oceniaj. Decyduj."
          showNotifications={false}
          rightSlot={
            <IconButton
              icon="settings-outline"
              label="Ustawienia"
              onPress={() => router.push('/settings')}
            />
          }
        />
        <DemoBanner />
      </View>
      <View style={{ gap: spacing.sm }}>
        <View style={styles.sectionRow}>
          <Text style={[typography.label, { color: colors.textMuted }]}>
            TWÓJ PRZEGLĄD RYNKU
          </Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <View
              style={{
                width: 5,
                height: 5,
                borderRadius: 3,
                backgroundColor: colors.accent,
              }}
            />
            <Text style={[typography.caption, { color: colors.accent }]}>
              {api.mode === 'demo' ? 'Demo' : 'Radar'}
            </Text>
          </View>
        </View>
        <View style={styles.stats}>
          <StatCard
            label="Oferty"
            icon="layers-outline"
            value={statsReady ? String(stats.count) : '—'}
            wide={width >= 640}
          />
          <StatCard
            label="Średni ROI"
            icon="trending-up-outline"
            value={statsReady ? formatRoiBps(stats.averageRoiBps) : '—'}
            wide={width >= 640}
          />
          <StatCard
            label="Hot deals"
            icon="flame-outline"
            value={statsReady ? String(stats.hotCount) : '—'}
            wide={width >= 640}
            description="Kandydaci BUY z dodatnim wynikiem."
          />
          <StatCard
            label="Potencjalny zysk"
            icon="wallet-outline"
            value={
              statsReady
                ? formatMoneyMinor(stats.potentialMinor, 'PLN', { emptyLabel: '—' })
                : '—'
            }
            accent
            wide={width >= 640}
          />
        </View>
        <Text style={[typography.caption, { color: colors.textSubtle }]}>
          Załadowane oferty · Suma dodatnich prognoz.
        </Text>
      </View>
      <View style={styles.searchRow}>
        <View
          style={[
            styles.search,
            {
              borderColor: searchFocused ? colors.accent : colors.border,
              backgroundColor: colors.surface,
              borderRadius: radii.lg,
            },
          ]}
        >
          <Ionicons
            name="search-outline"
            size={19}
            color={searchFocused ? colors.accent : colors.textSubtle}
          />
          <TextInput
            accessibilityLabel="Szukaj ofert"
            placeholder="Model, marka lub słowo kluczowe"
            placeholderTextColor={colors.textSubtle}
            value={filters.query}
            autoCorrect={false}
            returnKeyType="search"
            selectionColor={colors.accent}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            onChangeText={(value) => setFilters((old) => ({ ...old, query: value }))}
            style={[
              typography.body,
              { flex: 1, minWidth: 0, color: colors.text, paddingVertical: spacing.lg },
            ]}
          />
          {filters.query ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Wyczyść wyszukiwanie"
              onPress={() => setFilters((old) => ({ ...old, query: '' }))}
              style={{
                minWidth: 44,
                minHeight: 44,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Ionicons name="close-circle" size={18} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Filtry${activeFilterCount ? `, aktywne: ${activeFilterCount}` : ''}`}
          accessibilityState={{ expanded: filtersOpen }}
          aria-expanded={filtersOpen}
          onPress={() => setFiltersOpen(true)}
          style={({ pressed }) => [
            styles.filter,
            {
              borderRadius: radii.lg,
              borderColor: activeFilterCount ? colors.accentMuted : colors.border,
              backgroundColor: activeFilterCount ? colors.accentBg : colors.surface,
              opacity: pressed ? 0.65 : 1,
            },
          ]}
        >
          <Ionicons
            name="options-outline"
            size={20}
            color={activeFilterCount ? colors.accent : colors.text}
          />
          {activeFilterCount ? (
            <Text
              style={[typography.caption, { color: colors.accent, fontWeight: '700' }]}
            >
              {activeFilterCount}
            </Text>
          ) : null}
        </Pressable>
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: spacing.sm }}
      >
        {CATEGORY_TABS.map((tab) => {
          const active = filters.category === tab.id;
          return (
            <Pressable
              key={tab.id}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              aria-selected={active}
              onPress={() => setFilters((old) => ({ ...old, category: tab.id }))}
              style={({ pressed }) => [
                styles.chip,
                {
                  borderRadius: radii.pill,
                  borderColor: active ? colors.accentMuted : colors.border,
                  backgroundColor: active ? colors.accentBg : colors.surface,
                  opacity: pressed ? 0.7 : 1,
                },
              ]}
            >
              <Text
                style={[
                  typography.caption,
                  {
                    color: active ? colors.accent : colors.textMuted,
                    fontWeight: active ? '700' : '500',
                  },
                ]}
              >
                {tab.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
      {notice ? (
        <View
          accessibilityLiveRegion="polite"
          style={[
            styles.notice,
            { backgroundColor: colors.accentBg, borderRadius: radii.md },
          ]}
        >
          <Text style={[typography.caption, { color: colors.text, flex: 1 }]}>
            {notice}
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Zamknij komunikat"
            onPress={() => setNotice('')}
            style={{ padding: 12 }}
          >
            <Ionicons name="close" size={16} color={colors.textMuted} />
          </Pressable>
        </View>
      ) : null}
      {radarQuery.isRefetchError && radarQuery.data ? (
        <ErrorState
          message="Nie udało się odświeżyć ofert. Poniżej widzisz ostatnio pobrane dane."
          onRetry={() => {
            void radarQuery.refetch();
          }}
          retrying={radarQuery.isRefetching}
        />
      ) : null}
      <View style={styles.sectionRow}>
        <Text style={[typography.headline, { color: colors.text }]}>
          Okazje dla Ciebie
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Zmień sortowanie"
          onPress={() => setFiltersOpen(true)}
          style={{ minHeight: 44, justifyContent: 'center' }}
        >
          <Text style={[typography.caption, { color: colors.textMuted }]}>
            {sortLabels[filters.sort]} ↓
          </Text>
        </Pressable>
      </View>
    </View>
  );
  return (
    <AppScreen padded={false} bottomInset={false}>
      <FlatList
        key={columns}
        data={items}
        numColumns={columns}
        keyExtractor={(item) => item.id}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        contentContainerStyle={{
          paddingHorizontal: spacing.lg,
          paddingBottom: spacing.lg,
          gap: spacing.md,
          flexGrow: 1,
        }}
        columnWrapperStyle={columns > 1 ? { gap: spacing.lg } : undefined}
        ListHeaderComponent={header}
        refreshControl={
          <RefreshControl
            refreshing={radarQuery.isRefetching && !radarQuery.isFetchingNextPage}
            onRefresh={() => {
              void radarQuery.refetch();
            }}
            tintColor={colors.accent}
            colors={[colors.accent]}
          />
        }
        onEndReached={() => {
          if (
            radarQuery.hasNextPage &&
            !radarQuery.isFetchingNextPage &&
            !radarQuery.isError
          )
            void radarQuery.fetchNextPage();
        }}
        onEndReachedThreshold={0.35}
        ListEmptyComponent={
          radarQuery.isError && radarQuery.data ? null : radarQuery.isPending ? (
            <LoadingSkeleton />
          ) : radarQuery.isError ? (
            <ErrorState
              message={apiErrorMessage(radarQuery.error)}
              onRetry={() => {
                void radarQuery.refetch();
              }}
              retrying={radarQuery.isFetching}
            />
          ) : (
            <EmptyState
              icon="search-outline"
              title="Brak pasujących okazji"
              description="Zmień kryteria wyszukiwania lub sprawdź nowe oferty za chwilę."
              actionLabel={
                activeFilterCount || filters.query ? 'Wyczyść filtry' : 'Odśwież radar'
              }
              onAction={() => {
                if (activeFilterCount || filters.query) setFilters(defaultFilters);
                else void radarQuery.refetch();
              }}
            />
          )
        }
        renderItem={({ item }) => (
          <View style={{ flex: 1, maxWidth: columns > 1 ? '49.2%' : '100%' }}>
            <ProductCard
              item={item}
              onPress={() => openOffer(item)}
              watched={watchedKeys.has(item.id)}
              watchLoading={
                watchMutation.isPending && watchMutation.variables?.item.id === item.id
              }
              watchDisabled={watchMutation.isPending}
              onWatch={() =>
                watchMutation.mutate({ item, remove: watchedKeys.has(item.id) })
              }
            />
          </View>
        )}
        ListFooterComponent={
          radarQuery.isFetchingNextPage ? (
            <LoadingSkeleton rows={1} />
          ) : radarQuery.isFetchNextPageError ? (
            <ErrorState
              message="Nie udało się pobrać kolejnych ofert. Wczytane okazje pozostają na liście."
              onRetry={() => {
                void radarQuery.fetchNextPage();
              }}
            />
          ) : radarQuery.hasNextPage ? (
            <PrimaryButton
              label="Wczytaj więcej ofert"
              variant="secondary"
              onPress={() => {
                void radarQuery.fetchNextPage();
              }}
            />
          ) : null
        }
      />
      <FilterSheet
        visible={filtersOpen}
        initial={filters}
        onClose={() => setFiltersOpen(false)}
        onApply={onApplyFilters}
        onSaveProfile={async (name, next) => {
          const updated = [
            { id: `${Date.now()}`, name, filters: next },
            ...profiles.filter((profile) => profile.name !== name),
          ];
          try {
            await saveProfiles(updated);
            setProfiles(updated);
            setNotice('Profil wyszukiwania został zapisany.');
          } catch {
            setNotice('Nie udało się zapisać profilu. Spróbuj ponownie.');
          }
        }}
      />
    </AppScreen>
  );
}
const styles = StyleSheet.create({
  sectionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  searchRow: { flexDirection: 'row', gap: 8 },
  search: {
    flex: 1,
    minWidth: 0,
    minHeight: 54,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingLeft: 12,
  },
  filter: {
    minWidth: 54,
    minHeight: 54,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    borderWidth: 1,
  },
  chip: {
    minHeight: 44,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderWidth: 1,
    justifyContent: 'center',
  },
  notice: { paddingLeft: 12, flexDirection: 'row', alignItems: 'center' },
});
