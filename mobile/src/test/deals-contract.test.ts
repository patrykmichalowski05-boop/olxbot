import { mapDemoDeal } from '@/api/mappers/deal';

describe('Finanse — poprawny kontrakt API v2', () => {
  it('nie pomija ceny zakupu, kosztow i zysku', () => {
    const deal = mapDemoDeal({
      id: 'demo-1',
      title: 'PC',
      status: 'SOLD',
      purchase_amount_minor: 150000,
      total_costs_minor: 15000,
      sale_amount_minor: 200000,
      profit_minor: 35000,
    });

    expect(deal.purchase_minor).toBe(150000);
    expect(deal.cost_minor).toBe(15000);
    expect(deal.sale_minor).toBe(200000);
    expect(deal.realized_profit_minor).toBe(35000);
  });

  it('nie podaje zrealizowanego zysku bez sprzedazy', () => {
    const deal = mapDemoDeal({
      id: 'demo-2',
      status: 'PURCHASED',
      purchase_amount_minor: 80000,
      total_costs_minor: 5000,
      sale_amount_minor: null,
      profit_minor: 12345,
    });

    expect(deal.status).toBe('BOUGHT');
    expect(deal.realized_profit_minor).toBeNull();
  });
});
