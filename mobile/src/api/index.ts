import { resolveAppMode } from '@/utils/config';
import { demoClient } from '@/api/demo/demoClient';
import * as liveAuth from '@/api/endpoints/auth';
import * as liveRadar from '@/api/endpoints/radar';
import * as liveListings from '@/api/endpoints/listings';
import * as liveUniversal from '@/api/endpoints/universal';
import * as liveDeals from '@/api/endpoints/deals';
import { mapListingDetail, mapRadarItem } from '@/api/mappers/opportunity';
import type { OpportunityDetail } from '@/features/opportunity/types';

export function getAppMode() {
  return resolveAppMode();
}

export const api = {
  mode: getAppMode(),

  async login(username: string, password: string) {
    if (getAppMode() === 'demo') {
      await demoClient.login(username, password);
      return;
    }
    await liveAuth.login(username, password);
  },

  async logout() {
    if (getAppMode() === 'demo') {
      await demoClient.logout();
      return;
    }
    await liveAuth.logout();
  },

  async me() {
    if (getAppMode() === 'demo') {
      return demoClient.me();
    }
    return liveAuth.fetchMe();
  },

  async radarPage(query: Parameters<typeof liveRadar.fetchRadarPage>[0]) {
    if (getAppMode() === 'demo') {
      const page = await demoClient.radarPage({
        beforeId: query.beforeId,
        q: query.q,
      });
      return {
        items: page.items,
        nextBeforeId: page.next_before_id,
      };
    }
    const page = await liveRadar.fetchRadarPage(query);
    return {
      items: page.items.map(mapRadarItem),
      nextBeforeId: page.next_before_id,
    };
  },

  async opportunityDetail(id: string): Promise<OpportunityDetail | null> {
    if (getAppMode() === 'demo') {
      const numeric = Number(id.replace(/\D/g, ''));
      const byListing = await demoClient.listing(numeric);
      if (byListing) return byListing;
      const page = await demoClient.radarPage({});
      return page.items.find((o) => o.id === id || String(o.snapshotId) === id) ?? null;
    }

    const listingId = Number(id);
    if (!Number.isFinite(listingId)) {
      return null;
    }
    const listing = await liveListings.fetchListing(listingId);
    const detail = mapListingDetail(listing);
    try {
      const history = await liveListings.fetchListingHistory(listingId);
      detail.priceHistory = history.map((row, index) => ({
        at: String(row.observed_at ?? row.created_at ?? index),
        priceMinor:
          typeof row.price_minor === 'number' ? row.price_minor : null,
        label: 'Historia ceny',
      }));
    } catch {
      // brak historii nie blokuje ekranu
    }
    return detail;
  },

  watchlist: {
    async list() {
      if (getAppMode() === 'demo') return demoClient.watchlist();
      return liveUniversal.fetchWatchlist();
    },
    async add(key: string, label: string) {
      if (getAppMode() === 'demo') return demoClient.addWatch(key, label);
      return liveUniversal.addWatchItem(key, label);
    },
    async remove(key: string) {
      if (getAppMode() === 'demo') return demoClient.closeWatch(key);
      return liveUniversal.closeWatchItem(key);
    },
  },

  analyze: {
    async submitManual(data: liveUniversal.ManualAnalysisInput) {
      if (getAppMode() === 'demo') {
        return demoClient.analyzeManual(data);
      }
      const result = await liveUniversal.analyzeManual(data);
      return { job_id: `sync-${Date.now()}`, result };
    },
    async pollJob(jobId: string) {
      if (getAppMode() === 'demo') {
        return demoClient.analyzeJob(jobId);
      }
      return { status: 'done' as const, result: undefined };
    },
  },

  deals: {
    list: () =>
      getAppMode() === 'demo' ? demoClient.deals() : liveDeals.fetchDeals(),
    get: (id: string) =>
      getAppMode() === 'demo' ? demoClient.deal(id) : liveDeals.fetchDeal(id),
    purchase: liveDeals.recordPurchase,
    cost: liveDeals.recordCost,
    sell: liveDeals.recordSale,
  },

  notifications: () =>
    getAppMode() === 'demo' ? demoClient.notifications() : [],
};
