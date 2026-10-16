export type BackendDecision =
  | 'BUY_CANDIDATE'
  | 'NEGOTIATE'
  | 'REVIEW'
  | 'WATCH'
  | 'SKIP'
  | 'NO_RELIABLE_VALUATION'
  | string;

const DECISION_LABELS: Record<string, string> = {
  BUY_CANDIDATE: 'Kandydat do zakupu',
  BUY: 'Kandydat do zakupu',
  NEGOTIATE: 'Negocjuj',
  REVIEW: 'Wymaga weryfikacji',
  WATCH: 'Obserwuj',
  SKIP: 'Pomiń',
  NO_RELIABLE_VALUATION: 'Brak wiarygodnej wyceny',
};

export function decisionLabel(decision: string | null | undefined): string {
  if (!decision) {
    return 'Nieznana decyzja';
  }
  const key = decision.toUpperCase();
  return DECISION_LABELS[key] ?? 'Wymaga weryfikacji';
}

export function decisionTone(
  decision: string,
): 'success' | 'risk' | 'loss' | 'neutral' {
  const key = decision.toUpperCase();
  if (key === 'BUY_CANDIDATE' || key === 'BUY') return 'success';
  if (key === 'NEGOTIATE' || key === 'REVIEW' || key === 'WATCH') return 'risk';
  if (key === 'SKIP' || key === 'NO_RELIABLE_VALUATION') return 'loss';
  return 'neutral';
}

export const CATEGORY_TABS = [
  { id: 'ALL', label: 'Wszystkie' },
  { id: 'CAR', label: 'Auta' },
  { id: 'ELECTRONICS', label: 'Elektronika' },
  { id: 'FASHION', label: 'Moda' },
  { id: 'OTHER', label: 'Pozostałe' },
] as const;

export type CategoryTabId = (typeof CATEGORY_TABS)[number]['id'];
