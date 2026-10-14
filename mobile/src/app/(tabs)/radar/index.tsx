import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FlatList, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { FilterSheet } from '@/components/FilterSheet';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { ProductCard } from '@/components/ProductCard';
import { PRODUCT_TABLE_MIN_WIDTH, ProductTableHeader, ProductTableRow } from '@/components/ProductTable';
import type { OpportunityCard } from '@/features/opportunity/types';
import { applyClientFilters, countActiveFilters, defaultFilters, loadFilters, loadProfiles, saveFilters, saveProfiles, type RadarFilters, type SavedFilterProfile } from '@/features/radar/filterStore';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';
import { CATEGORY_TABS } from '@/utils/labels';

const sorts: { id: RadarFilters['sort']; label: string }[] = [
  { id: 'fresh', label: 'Najnowsze' }, { id: 'profit', label: 'Największy zysk' },
  { id: 'roi', label: 'Najwyższe ROI' }, { id: 'price', label: 'Najniższa cena' },
  { id: 'quality', label: 'Jakość wyceny' },
];

export default function RadarScreen() {
  const router = useRouter();
  const { search } = useLocalSearchParams<{ search?: string }>();
  const queryClient = useQueryClient();
  const { colors, typography, radii } = useTheme();
  const { isMobile, columns, contentWidth } = useResponsiveLayout();
  const [filters, setFilters] = useState<RadarFilters>(defaultFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sortOpen, setSortOpen] = useState(false);
  const [profiles, setProfiles] = useState<SavedFilterProfile[]>([]);
  const [view, setView] = useState<'cards' | 'table'>('cards');
  const effectiveFilters = { ...filters, query: typeof search === 'string' ? search : filters.query };
  const query = useDebouncedValue(effectiveFilters.query);

  useEffect(() => {
    void loadFilters().then(setFilters);
    void loadProfiles().then(setProfiles);
  }, []);

  const radarQuery = useInfiniteQuery({
    queryKey: ['radar', query, api.mode],
    initialPageParam: null as number | null,
    queryFn: ({ pageParam, signal }) => api.radarPage({ beforeId: pageParam, q: query, signal }),
    getNextPageParam: (last) => last.nextBeforeId,
  });
  const watchQuery = useQuery({ queryKey: ['watchlist', api.mode], queryFn: () => api.watchlist.list() });
  const watchKeys = new Set(watchQuery.data?.map((item) => item.listing_key) ?? []);
  const watchedKey = (item: OpportunityCard) => watchKeys.has(item.id) ? item.id :
    item.listingId !== undefined && watchKeys.has(`listing:${item.listingId}`) ? `listing:${item.listingId}` : null;

  const loaded = useMemo(() => {
    const flat = radarQuery.data?.pages.flatMap((page) => page.items) ?? [];
    return [...new Map(flat.map((item) => [item.id, item])).values()];
  }, [radarQuery.data]);
  const items = useMemo(() => applyClientFilters(loaded, filters), [loaded, filters]);
  const watchMutation = useMutation({
    mutationFn: async (item: OpportunityCard) => {
      const existing = watchedKey(item);
      if (existing) await api.watchlist.remove(existing);
      else await api.watchlist.add(item.id, item.title);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });
  const onApplyFilters = useCallback(async (next: RadarFilters) => {
    setFilters(next);
    router.setParams({ search: next.query });
    setFiltersOpen(false);
    await saveFilters(next);
  }, [router]);
  const changeFilters = (patch: Partial<RadarFilters>) => {
    const next = { ...effectiveFilters, ...patch };
    setFilters(next);
    void saveFilters(next);
  };
  const openOffer = (item: OpportunityCard) => router.push({
    pathname: '/offer/[id]', params: { id: String(item.listingId ?? item.snapshotId) },
  });
  const table = !isMobile && view === 'table';
  const cardWidth = (contentWidth - (columns - 1) * 16) / columns;
  const filterCount = countActiveFilters(filters);

  const list = (
    <FlatList
      key={table ? 'table' : `cards-${columns}`}
      testID={table ? 'radar-table' : 'radar-grid'}
      data={items}
      numColumns={table ? 1 : columns}
      keyExtractor={(item) => item.id}
      columnWrapperStyle={!table && columns > 1 ? { gap: 16 } : undefined}
      contentContainerStyle={table ? { paddingBottom: 16 } : { gap: 16, paddingBottom: 16 }}
      ListHeaderComponent={table ? <ProductTableHeader /> : null}
      stickyHeaderIndices={table ? [0] : undefined}
      refreshControl={<RefreshControl tintColor={colors.accent} refreshing={radarQuery.isRefetching} onRefresh={() => void radarQuery.refetch()} />}
      onEndReached={() => {
        if (radarQuery.hasNextPage && !radarQuery.isFetchingNextPage) void radarQuery.fetchNextPage();
      }}
      onEndReachedThreshold={0.4}
      ListEmptyComponent={<EmptyState title="Brak okazji" description="Zmień filtry albo odśwież listę." actionLabel="Resetuj filtry" onAction={() => void onApplyFilters(defaultFilters)} />}
      renderItem={({ item }) => table ? (
        <ProductTableRow item={item} onPress={() => openOffer(item)} onWatch={() => watchMutation.mutate(item)}
          watched={Boolean(watchedKey(item))} pending={watchMutation.isPending && watchMutation.variables?.id === item.id} />
      ) : (
        <View style={{ width: cardWidth }}>
          <ProductCard item={item} onPress={() => openOffer(item)} onWatch={() => watchMutation.mutate(item)}
            watched={Boolean(watchedKey(item))} watchPending={watchMutation.isPending && watchMutation.variables?.id === item.id} />
        </View>
      )}
      ListFooterComponent={radarQuery.isFetchingNextPage ? <LoadingSkeleton rows={1} /> : radarQuery.hasNextPage ? (
        <Pressable accessibilityRole="button" onPress={() => void radarQuery.fetchNextPage()} style={[styles.loadMore, { borderColor: colors.border }]}>
          <Text style={[typography.bodyStrong, { color: colors.accent }]}>Wczytaj więcej ofert</Text>
        </Pressable>
      ) : null}
    />
  );

  return (
    <AppScreen>
      <Header title="Radar okazji" subtitle="Wyszukuj, porównuj i oceniaj potencjał ofert" />
      <DemoBanner />
      <View style={[styles.filterPanel, { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radii.lg }]}>
        <View style={styles.toolbar}>
          <View style={[styles.search, { backgroundColor: colors.background, borderColor: colors.border }]}>
            <Ionicons name="search-outline" size={18} color={colors.textMuted} />
            <TextInput accessibilityLabel="Szukaj modelu lub marki" placeholder="Szukaj modelu, marki…" placeholderTextColor={colors.textMuted}
              value={effectiveFilters.query} onChangeText={(text) => { router.setParams({ search: text }); changeFilters({ query: text }); }}
              style={[styles.searchInput, { color: colors.text }]} />
          </View>
          <Pressable accessibilityRole="button" accessibilityLabel="Otwórz filtry" onPress={() => setFiltersOpen(true)} style={[styles.control, { borderColor: colors.border }]}>
            <Ionicons name="options-outline" size={17} color={colors.textMuted} />
            <Text style={[typography.caption, { color: colors.text, fontWeight: '600' }]}>Filtry{filterCount ? ` (${filterCount})` : ''}</Text>
          </Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel="Sortowanie ofert" accessibilityState={{ expanded: sortOpen }} onPress={() => setSortOpen(!sortOpen)} style={[styles.control, { borderColor: colors.border }]}>
            <Ionicons name="swap-vertical-outline" size={16} color={colors.textMuted} />
            <Text style={[typography.caption, { color: colors.text }]}>{sorts.find((sort) => sort.id === filters.sort)?.label}</Text>
          </Pressable>
          {!isMobile ? <View style={[styles.viewSwitch, { backgroundColor: colors.background, borderColor: colors.border }]}>
            {(['cards', 'table'] as const).map((mode) => <Pressable key={mode} accessibilityRole="button"
              accessibilityLabel={mode === 'cards' ? 'Widok kart' : 'Widok tabeli'} accessibilityState={{ selected: view === mode }}
              onPress={() => setView(mode)} style={[styles.viewButton, { backgroundColor: view === mode ? colors.accentMuted : 'transparent' }]}>
              <Ionicons name={mode === 'cards' ? 'grid-outline' : 'list-outline'} size={18} color={view === mode ? colors.accent : colors.textMuted} />
            </Pressable>)}
          </View> : null}
        </View>
        {sortOpen ? <View style={styles.chips}>{sorts.map((sort) => <Pressable key={sort.id} accessibilityRole="button" accessibilityState={{ selected: filters.sort === sort.id }} onPress={() => { changeFilters({ sort: sort.id }); setSortOpen(false); }} style={[styles.chip, { backgroundColor: colors.background }]}>
          <Text style={[typography.caption, { color: filters.sort === sort.id ? colors.accent : colors.textMuted }]}>{sort.label}</Text>
        </Pressable>)}</View> : null}
        <View style={styles.chips}>
          {CATEGORY_TABS.map((tab) => <Pressable key={tab.id} accessibilityRole="button" accessibilityState={{ selected: filters.category === tab.id }}
            onPress={() => changeFilters({ category: tab.id })} style={[styles.chip, { backgroundColor: filters.category === tab.id ? colors.accentMuted : colors.background }]}>
            <Text style={[typography.caption, { color: filters.category === tab.id ? colors.accent : colors.textMuted, fontWeight: '600' }]}>{tab.label}</Text>
          </Pressable>)}
          {filterCount > 0 ? <Pressable accessibilityRole="button" onPress={() => void onApplyFilters(defaultFilters)} style={styles.chip}>
            <Text style={[typography.caption, { color: colors.accent }]}>Resetuj</Text>
          </Pressable> : null}
        </View>
        {profiles.length ? <View style={styles.chips}><Text style={[typography.caption, { color: colors.textMuted }]}>Profile:</Text>{profiles.map((profile) => <Pressable key={profile.id} accessibilityRole="button" onPress={() => void onApplyFilters(profile.filters)} style={styles.chip}>
          <Text style={[typography.caption, { color: colors.accent }]}>{profile.name}</Text>
        </Pressable>)}</View> : null}
      </View>
      <View style={styles.results}>
        <Text style={[typography.caption, { color: colors.textMuted }]}>{radarQuery.isLoading ? 'Pobieranie ofert…' : `${items.length} ofert · ${loaded.length} pobranych`}</Text>
        {!isMobile ? <Text style={[typography.caption, { color: colors.textMuted }]}>Filtry i sortowanie dotyczą pobranych ofert</Text> : null}
      </View>
      {watchMutation.isError ? <Text accessibilityRole="alert" style={[typography.caption, { color: colors.loss, marginBottom: 12 }]}>{apiErrorMessage(watchMutation.error)}</Text> : null}
      {radarQuery.isLoading ? <LoadingSkeleton /> : radarQuery.isError ? <ErrorState message={apiErrorMessage(radarQuery.error)} onRetry={() => void radarQuery.refetch()} /> :
        table ? <ScrollView horizontal style={{ flex: 1 }} contentContainerStyle={{ flexGrow: 1 }}>
          <View style={{ width: Math.max(contentWidth, PRODUCT_TABLE_MIN_WIDTH), flex: 1 }}>{list}</View>
        </ScrollView> : list}
      <FilterSheet visible={filtersOpen} initial={effectiveFilters} onClose={() => setFiltersOpen(false)} onApply={(next) => void onApplyFilters(next)}
        onSaveProfile={async (name, next) => {
          const updated = [{ id: `${Date.now()}`, name, filters: next }, ...profiles.filter((profile) => profile.name !== name)];
          setProfiles(updated);
          await saveProfiles(updated);
        }} />
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  filterPanel: { padding: 16, borderWidth: 1, gap: 14 },
  toolbar: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, alignItems: 'center' },
  search: { flex: 1, minWidth: 180, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 12, borderWidth: 1, borderRadius: 10 },
  searchInput: { flex: 1, minWidth: 0, height: 44, fontSize: 13 },
  control: { minHeight: 44, paddingHorizontal: 12, borderWidth: 1, borderRadius: 10, flexDirection: 'row', alignItems: 'center', gap: 6 },
  viewSwitch: { flexDirection: 'row', padding: 3, borderWidth: 1, borderRadius: 10 },
  viewButton: { width: 42, height: 38, borderRadius: 7, alignItems: 'center', justifyContent: 'center' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  chip: { minHeight: 36, paddingHorizontal: 12, paddingVertical: 9, borderRadius: 8 },
  results: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, marginVertical: 16 },
  loadMore: { minHeight: 48, borderWidth: 1, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginTop: 12 },
});
