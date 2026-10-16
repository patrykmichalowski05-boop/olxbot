import type { FinancialDeal } from "@/api/mappers/deal";

export function hasKnownFinancials(deal: FinancialDeal): boolean {
  return (
    deal.financials_complete !== false &&
    Number.isSafeInteger(deal.purchase_minor) &&
    Number.isSafeInteger(deal.cost_minor)
  );
}

export function dealSummary(items: FinancialDeal[]) {
  const sold = items.filter((item) => item.status === "SOLD");
  const open = items.filter((item) =>
    [
      "BOUGHT",
      "PURCHASED",
      "PICKUP",
      "PREPARING",
      "READY_TO_SELL",
      "LISTED",
    ].includes(item.status),
  );
  const all = (rows: FinancialDeal[]) => rows.every(hasKnownFinancials);
  return {
    sold: sold.length,
    open: open.length,
    profit: sold.every((item) =>
      Number.isSafeInteger(item.realized_profit_minor),
    )
      ? sold.reduce((sum, item) => sum + item.realized_profit_minor!, 0)
      : null,
    capital: all(open)
      ? open.reduce(
          (sum, item) => sum + item.purchase_minor + item.cost_minor,
          0,
        )
      : null,
    inventory: all(open)
      ? open.reduce((sum, item) => sum + item.purchase_minor, 0)
      : null,
    costs: all(items)
      ? items.reduce((sum, item) => sum + item.cost_minor, 0)
      : null,
    incomplete: items.filter((item) => !hasKnownFinancials(item)).length,
  };
}
