export type FinancialDeal = {
  financials_complete?: boolean;
  id: string;
  listing_id?: string;
  title?: string | null;
  status: string;
  purchase_minor: number;
  cost_minor: number;
  sale_minor: number | null;
  realized_profit_minor: number | null;
  currency?: string;
  created_at?: string;
};

type LegacyDemoDeal = {
  id: string;
  title?: string;
  status: string;
  purchase_amount_minor: number;
  total_costs_minor: number;
  sale_amount_minor: number | null;
  profit_minor: number | null;
  updated_at?: string;
};

export function mapDemoDeal(deal: LegacyDemoDeal): FinancialDeal {
  return {
    id: deal.id,
    title: deal.title,
    status: deal.status === "PURCHASED" ? "BOUGHT" : deal.status,
    purchase_minor: deal.purchase_amount_minor,
    cost_minor: deal.total_costs_minor,
    sale_minor: deal.sale_amount_minor,
    realized_profit_minor: deal.status === "SOLD" ? deal.profit_minor : null,
    currency: "PLN",
    created_at: deal.updated_at,
  };
}
