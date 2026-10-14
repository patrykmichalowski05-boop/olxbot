import type { FinancialDeal } from '@/api/mappers/deal';
import type { OpportunityCard } from '@/features/opportunity/types';
import { summarizeDeals, summarizeRadar } from '@/features/dashboard/summary';

const deal: FinancialDeal = { id: 'a', status: 'SOLD', purchase_minor: 10000, cost_minor: 1000, sale_minor: 20000, realized_profit_minor: 7777, currency: 'PLN' };

describe('Dashboard: wyłącznie dane zwrócone przez API', () => {
  it('nie pokazuje zer przed odpowiedzią endpointu', () => {
    expect(summarizeDeals(undefined).profitMinor).toBeNull();
    expect(summarizeRadar(undefined).active).toBeNull();
  });
  it('sumuje zwrócony wynik, bez ponownego liczenia z cen', () => {
    expect(summarizeDeals([deal]).profitMinor).toBe(7777);
  });
  it('nie zastępuje brakującego wyniku sprzedanego flipu zerem', () => {
    expect(summarizeDeals([deal, { ...deal, id: 'b', realized_profit_minor: null }]).profitMinor).toBeNull();
  });
  it('odróżnia pustą odpowiedź od braku danych i nie sumuje walut', () => {
    expect(summarizeDeals([]).profitMinor).toBe(0);
    expect(summarizeDeals([{ ...deal, currency: 'EUR' }]).profitMinor).toBeNull();
  });
  it('nie uznaje nieznanego statusu źródła za aktywną ofertę', () => {
    expect(summarizeRadar([{ sourceStatus: 'UNKNOWN', decision: 'REVIEW' } as OpportunityCard])).toEqual({ active: null, attention: 1 });
  });
  it('nie traktuje nieznanego statusu transakcji jako zakupionego flipu', () => {
    expect(summarizeDeals([{ ...deal, status: 'UNKNOWN' }]).active).toBeNull();
  });
  it('uwzględnia wystawione flipy z istniejącego DEMO', () => {
    const stats = summarizeDeals([{ ...deal, id: 'listed', status: 'LISTED', realized_profit_minor: null }, deal]);
    expect(stats.active).toBe(1);
    expect(stats.profitMinor).toBe(7777);
  });
});
