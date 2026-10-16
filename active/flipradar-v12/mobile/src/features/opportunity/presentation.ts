import type { OpportunityCard } from "./types";

export function radarSummary(items: OpportunityCard[]) {
  const valued = items.filter((item) => item.hasValuation);
  const rois = valued.flatMap((item) =>
    item.roiBps !== null && Number.isFinite(item.roiBps) ? [item.roiBps] : [],
  );
  const profits = valued.flatMap((item) =>
    item.operatingProfitMinor !== null &&
    Number.isFinite(item.operatingProfitMinor)
      ? [item.operatingProfitMinor]
      : [],
  );
  return {
    count: items.length,
    averageRoiBps: rois.length
      ? Math.round(rois.reduce((sum, value) => sum + value, 0) / rois.length)
      : null,
    hotCount: valued.filter((item) => isHotDeal(item)).length,
    potentialMinor: profits.length
      ? profits.reduce((sum, value) => sum + Math.max(0, value), 0)
      : items.length
        ? null
        : 0,
  };
}

/** A hot deal is a valued BUY candidate with a positive operating result. */
export function isHotDeal(item: OpportunityCard): boolean {
  return (
    item.hasValuation &&
    ["BUY", "BUY_CANDIDATE"].includes(item.decision.toUpperCase()) &&
    (item.operatingProfitMinor ?? 0) > 0
  );
}

export function opportunityRisk(item: OpportunityCard): {
  label: string;
  tone: "warning" | "danger" | "neutral";
} {
  if (!item.hasValuation)
    return { label: "Ryzyko nieocenione", tone: "neutral" };
  if (
    item.confidence?.toUpperCase() === "LOW" ||
    /podróbk|uszkod|fraud|scam/i.test(item.topRisk ?? "")
  ) {
    return { label: "Wysokie ryzyko", tone: "danger" };
  }
  // Missing risk data must never be presented as proof of low risk.
  return item.topRisk
    ? { label: "Do weryfikacji", tone: "warning" }
    : { label: "Ryzyko nieocenione", tone: "neutral" };
}

export function opportunityInsight(item: OpportunityCard): {
  label: string;
  text: string;
} {
  if (item.insight?.trim())
    return {
      label: item.insightSource === "rules" ? "Analiza rynku" : "Insight AI",
      text: item.insight.trim(),
    };
  return {
    label: "Sygnał z analizy",
    text: !item.hasValuation
      ? "Za mało danych do wiarygodnej wyceny. Sprawdź model i stan przed zakupem."
      : item.topRisk
        ? item.topRisk
        : isHotDeal(item)
          ? "Dodatni wynik w prognozie. Zweryfikuj stan i koszty przed zakupem."
          : "Porównaj cenę, koszty i stan przedmiotu przed podjęciem decyzji.",
  };
}
