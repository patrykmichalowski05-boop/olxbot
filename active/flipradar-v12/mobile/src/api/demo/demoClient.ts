import type { OpportunityDetail } from "@/features/opportunity/types";
import type {
  UniversalWatchItem,
  ManualAnalysisInput,
  ManualAnalysisResult,
} from "@/api/endpoints/universal";
import { workspaceDemoOffers } from "./workspaceFixtures";
import {
  demoDeals,
  demoNotifications,
  demoOpportunities,
  demoWatchlist,
} from "./fixtures";

let watchlist = [...demoWatchlist];
let deals = [...demoDeals];
const analyzeJobs = new Map<
  string,
  { status: "running" | "done" | "error"; result?: ManualAnalysisResult }
>();

function delay(ms = 400) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const demoClient = {
  async login(_username: string, _password: string) {
    await delay();
    return { ok: true };
  },
  async logout() {
    await delay(100);
  },
  async me() {
    return { user_id: "demo-user", access: "demo" };
  },
  async radarPage(query: { beforeId?: number | null; q?: string }) {
    await delay();
    let items = [...workspaceDemoOffers, ...demoOpportunities];
    if (query.q?.trim()) {
      const q = query.q.toLowerCase();
      items = items.filter((item) => item.title.toLowerCase().includes(q));
    }
    if (query.beforeId) {
      items = items.filter((item) => item.snapshotId < query.beforeId!);
    }
    const slice = items.slice(0, 20);
    return {
      items: slice,
      next_before_id:
        slice.length > 0 && items.length > slice.length
          ? slice[slice.length - 1]!.snapshotId
          : null,
    };
  },
  async listing(id: number): Promise<OpportunityDetail | null> {
    await delay();
    return (
      [...workspaceDemoOffers, ...demoOpportunities].find(
        (item) => item.listingId === id,
      ) ?? null
    );
  },
  async watchlist(): Promise<UniversalWatchItem[]> {
    await delay();
    return watchlist;
  },
  async addWatch(key: string, label: string) {
    await delay();
    watchlist = [
      { listing_key: key, label, updated: new Date().toISOString() },
      ...watchlist.filter((w) => w.listing_key !== key),
    ];
  },
  async closeWatch(key: string) {
    await delay();
    watchlist = watchlist.filter((w) => w.listing_key !== key);
  },
  async analyzeManual(data: ManualAnalysisInput): Promise<{ job_id: string }> {
    await delay(200);
    const jobId = `demo-job-${Date.now()}`;
    analyzeJobs.set(jobId, { status: "running" });
    setTimeout(() => {
      analyzeJobs.set(jobId, {
        status: "done",
        result: {
          decision: data.title.toLowerCase().includes("bmw")
            ? "NEGOTIATE"
            : "REVIEW",
          reasons: ["Analiza demonstracyjna — bez połączenia z backendem"],
          snapshot_id: 9999,
        },
      });
    }, 1200);
    return { job_id: jobId };
  },
  async analyzeJob(jobId: string) {
    await delay(100);
    return analyzeJobs.get(jobId) ?? { status: "error" as const };
  },
  notifications() {
    return demoNotifications;
  },
  deals() {
    return { items: deals, next_before_id: null };
  },
  deal(id: string) {
    return deals.find((d) => d.id === id) ?? null;
  },
  recordPurchase(listingId: string, amountMinor: number) {
    deals = [
      {
        id: `deal-${Date.now()}`,
        title: `Flip ${listingId}`,
        status: "PURCHASED",
        purchase_amount_minor: amountMinor,
        total_costs_minor: 0,
        sale_amount_minor: null,
        profit_minor: null,
        updated_at: new Date().toISOString(),
      },
      ...deals,
    ];
    return deals[0];
  },
};
