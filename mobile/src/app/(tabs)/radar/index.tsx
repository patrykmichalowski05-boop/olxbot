import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  FlatList,
  Linking,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';

import { api } from '@/api';
import { radarSource } from '@/utils/config';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { ErrorState } from '@/components/ErrorState';
import { FilterSheet } from '@/components/FilterSheet';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { ProductCard } from '@/components/ProductCard';
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
import { useTheme } from '@/theme/ThemeProvider';
import { CATEGORY_TABS } from '@/utils/labels';

export default function RadarScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { colors, spacing, typography, radii } = useTheme();

  const [filters, setFilters] = useState<RadarFilters>(defaultFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [profiles, setProfiles] = useState<SavedFilterProfile[]>([]);
  const listRef = useRef<FlatList>(null);

  useEffect(() => {
    void loadFilters().then(setFilters);
    void loadProfiles().then(setProfiles);
  }, []);

  const radarQuery = useInfiniteQuery({
    queryKey: ['radar', filters.query, api.mode],
    initialPageParam: null as number | null,
    queryFn: async ({ pageParam, signal }) => {
      const page = await api.radarPage({
        beforeId: pageParam,
        q: filters.query,
        signal,
      });
      return page;
    },
    getNextPageParam: (last) => last.nextBeforeId,
  });

  const items = useMemo(() => {
    const flat = radarQuery.data?.pages.flatMap((p) => p.items) ?? [];
    const dedup = new Map<string, (typeof flat)[number]>();
    for (const item of flat) {
      dedup.set(item.id, item);
    }
    return applyClientFilters([...dedup.values()], filters);
  }, [radarQuery.data, filters]);

  const watchMutation = useMutation({
    mutationFn: async (item: (typeof items)[number]) => {
      const key = item.id;
      await api.watchlist.add(key, item.title);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const activeFilterCount = countActiveFilters(filters);

  const onApplyFilters = useCallback(async (next: RadarFilters) => {
    setFilters(next);
    await saveFilters(next);
    setFiltersOpen(false);
    await queryClient.invalidateQueries({ queryKey: ['radar'] });
  }, [queryClient]);

  return (
    <AppScreen padded={false}>
      <View style={{ paddingHorizontal: spacing.lg, paddingTop: spacing.sm }}>
        <Header title="Radar okazji" subtitle="Profil: manualny" />
        <DemoBanner />

        <TextInput
          placeholder="Szukaj modelu, marki…"
          placeholderTextColor={colors.textMuted}
          value={filters.query}
          onChangeText={(query) => setFilters((f) => ({ ...f, query }))}
          style={[
            styles.search,
            {
              color: colors.text,
              borderColor: colors.border,
              backgroundColor: colors.surface,
              borderRadius: radii.md,
              padding: spacing.md,
            },
          ]}
        />

        <View style={[styles.toolbar, { marginVertical: spacing.sm }]}>
          <Pressable
            onPress={() => setFiltersOpen(true)}
            style={[styles.filterBtn, { borderColor: colors.border, borderRadius: radii.md }]}
          >
            <Text style={[typography.bodyStrong, { color: colors.text }]}>
              Filtry{activeFilterCount ? ` (${activeFilterCount})` : ''}
            </Text>
          </Pressable>
          {activeFilterCount > 0 ? (
            <Pressable onPress={() => onApplyFilters(defaultFilters)}>
              <Text style={[typography.caption, { color: colors.accent }]}>Resetuj</Text>
            </Pressable>
          ) : null}
        </View>

        <View style={styles.categories}>
          {CATEGORY_TABS.map((tab) => {
            const active = filters.category === tab.id;
            return (
              <Pressable
                key={tab.id}
                onPress={() => setFilters((f) => ({ ...f, category: tab.id }))}
                style={[
                  styles.chip,
                  {
                    backgroundColor: active ? colors.accent : colors.surface,
                    borderRadius: radii.pill,
                  },
                ]}
              >
                <Text
                  style={[
                    typography.caption,
                    { color: active ? colors.background : colors.text },
                  ]}
                >
                  {tab.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {radarQuery.isLoading ? (
        <View style={{ padding: spacing.lg }}>
          <LoadingSkeleton />
        </View>
      ) : radarQuery.isError ? (
        <ErrorState
          message={apiErrorMessage(radarQuery.error)}
          onRetry={() => radarQuery.refetch()}
        />
      ) : (
        <FlatList
          ref={listRef}
          data={items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
          refreshControl={
            <RefreshControl
              refreshing={radarQuery.isRefetching}
              onRefresh={() => radarQuery.refetch()}
            />
          }
          onEndReached={() => {
            if (radarQuery.hasNextPage && !radarQuery.isFetchingNextPage) {
              void radarQuery.fetchNextPage();
            }
          }}
          onEndReachedThreshold={0.4}
          ListEmptyComponent={
            <EmptyState
              title="Brak okazji"
              description="Zmień filtry albo odśwież listę."
            />
          }
          renderItem={({ item }) => (
            <ProductCard
              item={item}
              onPress={() => {
                if (
                  api.mode === 'live' &&
                  radarSource() === 'legacy' &&
                  !item.listingId
                ) {
                  if (item.url) {
                    void Linking.openURL(item.url).catch(() => undefined);
                  }
                  return;
                }

                router.push({
                  pathname: '/offer/[id]',
                  params: {
                    id: item.listingId
                      ? String(item.listingId)
                      : item.id,
                  },
                });
              }}
              onWatch={() => watchMutation.mutate(item)}
            />
          )}
          ListFooterComponent={
            radarQuery.isFetchingNextPage ? (
              <LoadingSkeleton rows={1} />
            ) : null
          }
        />
      )}

      <FilterSheet
        visible={filtersOpen}
        initial={filters}
        onClose={() => setFiltersOpen(false)}
        onApply={onApplyFilters}
        onSaveProfile={async (name, next) => {
          const updated = [
            { id: `${Date.now()}`, name, filters: next },
            ...profiles.filter((p) => p.name !== name),
          ];
          setProfiles(updated);
          await saveProfiles(updated);
        }}
      />
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  search: { borderWidth: 1, marginTop: 8 },
  toolbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  filterBtn: {
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  categories: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  chip: { paddingHorizontal: 10, paddingVertical: 6 },
});
