import React from 'react';
import { Badge } from './Badge';
import { decisionLabel, decisionTone } from '@/utils/labels';

export function DecisionBadge({
  decision,
  compact = false,
}: {
  decision: string;
  compact?: boolean;
}) {
  const tone = decisionTone(decision);
  const key = decision.toUpperCase();
  const label = compact
    ? ['BUY_CANDIDATE', 'BUY'].includes(key)
      ? 'BUY'
      : key === 'SKIP' || key === 'NO_RELIABLE_VALUATION'
        ? 'SKIP'
        : 'WATCH'
    : decisionLabel(decision);
  return (
    <Badge
      label={label}
      accessibilityLabel={`Decyzja: ${decisionLabel(decision)}`}
      tone={
        tone === 'success'
          ? 'success'
          : tone === 'risk'
            ? 'warning'
            : tone === 'loss'
              ? 'danger'
              : 'neutral'
      }
    />
  );
}
