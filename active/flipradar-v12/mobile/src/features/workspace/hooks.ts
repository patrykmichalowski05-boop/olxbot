import type { RadarFilters } from "@/features/radar/filterStore";
import { useMemo, useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import type { UniversalWatchItem } from "@/api/endpoints/universal";
import type { OpportunityCard } from "@/features/opportunity/types";
import { useAuth } from "@/features/auth/AuthContext";
import { useRuntimeCapabilities } from "@/features/runtime/useRuntimeCapabilities";
import { savedKeyFor } from "./presentation";

export function useRadarOffers(
  query = "",
  enabled = true,
  filters?: RadarFilters,
) {
  const { ready, signedIn, userId } = useAuth();
  const request = useInfiniteQuery({
    queryKey: ["workspace-offers", api.mode, userId, query, filters ?? null],
    enabled: ready && signedIn && enabled,
    initialPageParam: null as number | null,
    queryFn: ({ pageParam, signal }) =>
      api.radarPage({
        beforeId: pageParam,
        q: query,
        signal,
        minPriceMinor: filters?.minBudgetMinor,
        maxPriceMinor: filters?.maxBudgetMinor,
        minProfitMinor: filters?.minProfitMinor,
        minRoiBps: filters?.minRoiBps,
        category: filters?.category,
        platforms: filters?.platforms,
      }),
    getNextPageParam: (last) => last.nextBeforeId ?? undefined,
  });
  const items = useMemo(
    () => [
      ...new Map(
        (request.data?.pages.flatMap((page) => page.items) ?? []).map(
          (item) => [item.id, item],
        ),
      ).values(),
    ],
    [request.data],
  );
  return { request, items };
}

export function useWatchActions() {
  const runtime = useRuntimeCapabilities();
  const { userId, ready, signedIn } = useAuth();
  const cache = useQueryClient();
  const [notice, setNotice] = useState("");
  const key = ["watchlist", api.mode, userId];
  const saved = useQuery({
    queryKey: key,
    queryFn: () => api.watchlist.list(),
    enabled:
      ready && signedIn && runtime.ready && runtime.capabilities.watchlist,
  });
  const watched = useMemo(
    () => new Set(saved.data?.map((item) => item.listing_key)),
    [saved.data],
  );
  const mutation = useMutation({
    mutationFn: ({
      item,
      remove,
      savedKey,
    }: {
      item: OpportunityCard;
      remove: boolean;
      savedKey: string;
    }) =>
      remove
        ? api.watchlist.remove(savedKey)
        : api.watchlist.add(item.id, item.title),
    onSuccess: (_, { item, remove, savedKey }) => {
      cache.setQueryData<UniversalWatchItem[]>(key, (old) =>
        remove
          ? old?.filter((row) => row.listing_key !== savedKey)
          : [
              {
                listing_key: item.id,
                label: item.title,
                updated: new Date().toISOString(),
              },
              ...(old ?? []).filter((row) => row.listing_key !== item.id),
            ],
      );
      void cache.invalidateQueries({ queryKey: ["watchlist"] });
      setNotice(
        remove
          ? "Oferta została usunięta z zapisanych."
          : "Oferta została zapisana.",
      );
    },
    onError: (error) => setNotice(apiErrorMessage(error)),
  });
  return {
    saved,
    available: runtime.ready && runtime.capabilities.watchlist,
    writable: runtime.canWrite,
    watched,
    isWatched: (item: OpportunityCard) => Boolean(savedKeyFor(item, watched)),
    mutation,
    notice,
    clearNotice: () => setNotice(""),
    toggle: (item: OpportunityCard) => {
      if (
        !runtime.canWrite ||
        !runtime.capabilities.watchlist ||
        mutation.isPending ||
        saved.isPending ||
        saved.isError
      )
        return;
      const existing = savedKeyFor(item, watched);
      mutation.mutate({
        item,
        remove: Boolean(existing),
        savedKey: existing ?? item.id,
      });
    },
  };
}
