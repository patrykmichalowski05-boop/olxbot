import type { FinancialDeal } from '@/api/mappers/deal';
import type { OpportunityCard } from '@/features/opportunity/types';

export const ACTIVE_DEAL_STATUSES = ['BOUGHT', 'LISTED'];

/** Presentation totals only: sum the backend amounts; never reconstruct profit. */
function sumMinor(values: (number | null | undefined)[]): number | null {
  if (values.some(value => value == null || !Number.isSafeInteger(value))) return null;
  const sum = values.reduce<number>((total, value) => total + (value as number), 0);
  return Number.isSafeInteger(sum) ? sum : null;
}

export function summarizeDeals(items: FinancialDeal[] | undefined) {
  if (!items) return { active: null, sold: null, profitMinor: null, inventoryMinor: null, costsMinor: null };
  const known = items.every(deal => ACTIVE_DEAL_STATUSES.includes(deal.status) || deal.status === 'SOLD');
  const pln = items.every(deal => !deal.currency || deal.currency === 'PLN');
  const active = items.filter(deal => ACTIVE_DEAL_STATUSES.includes(deal.status));
  const sold = items.filter(deal => deal.status === 'SOLD');
  return {
    active: known ? active.length : null,
    sold: known ? sold.length : null,
    profitMinor: known && pln ? sumMinor(sold.map(deal => deal.realized_profit_minor)) : null,
    inventoryMinor: known && pln ? sumMinor(active.map(deal => deal.purchase_minor)) : null,
    costsMinor: pln ? sumMinor(items.map(deal => deal.cost_minor)) : null,
  };
}

export function summarizeRadar(items: OpportunityCard[] | undefined) {
  if (!items) return { active: null, attention: null };
  const knownStatus = items.every(item => ['ACTIVE', 'UNAVAILABLE', 'IMPORT_ONLY'].includes(item.sourceStatus));
  const decisions = ['BUY_CANDIDATE', 'NEGOTIATE', 'REVIEW', 'WATCH', 'SKIP', 'NO_RELIABLE_VALUATION'];
  return {
    active: knownStatus ? items.filter(item => item.sourceStatus === 'ACTIVE').length : null,
    attention: items.every(item => decisions.includes(item.decision))
      ? items.filter(item => ['BUY_CANDIDATE', 'NEGOTIATE', 'REVIEW'].includes(item.decision)).length : null,
  };
}
