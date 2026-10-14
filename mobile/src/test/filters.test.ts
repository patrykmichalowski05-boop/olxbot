import { applyClientFilters, defaultFilters } from '@/features/radar/filterStore';
import type { OpportunityCard } from '@/features/opportunity/types';

const sample: OpportunityCard[] = [
  {
    id: '1',
    snapshotId: 1,
    title: 'PC',
    platform: 'OLX',
    purchaseMinor: 100000,
    operatingProfitMinor: 50000,
    roiBps: 5000,
    decision: 'WATCH',
    verifiedAt: null,
    url: null,
    category: 'ELECTRONICS',
    sourceStatus: 'ACTIVE',
    hasValuation: true,
  },
  {
    id: '2',
    snapshotId: 2,
    title: 'BMW',
    platform: 'OTOMOTO',
    purchaseMinor: 5000000,
    operatingProfitMinor: 100000,
    roiBps: 200,
    decision: 'SKIP',
    verifiedAt: null,
    url: null,
    category: 'CAR',
    sourceStatus: 'ACTIVE',
    hasValuation: false,
  },
];

describe('applyClientFilters', () => {
  it('filters by category and min profit', () => {
    const result = applyClientFilters(sample, {
      ...defaultFilters,
      category: 'ELECTRONICS',
      minProfitMinor: 40000,
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.id).toBe('1');
  });
});

describe('Budget safety', () => {
  it('rejects unknown and excessive prices', () => {
    const unknown = {
      ...sample[0],
      id: 'unknown',
      purchaseMinor: null,
    };
    const result = applyClientFilters(
      [...sample, unknown],
      { ...defaultFilters, maxBudgetMinor: 150000 },
    );
    expect(result.map((item) => item.id)).toEqual(['1']);
  });
});
