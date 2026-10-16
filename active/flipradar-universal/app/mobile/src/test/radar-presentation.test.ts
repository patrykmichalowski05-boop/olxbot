import { demoOpportunities } from '@/api/demo/fixtures';
import {
  isHotDeal,
  opportunityInsight,
  opportunityRisk,
  radarSummary,
} from '@/features/opportunity/presentation';

describe('Radar presentation', () => {
  it('summarizes only loaded and reliable financial values', () => {
    const summary = radarSummary(demoOpportunities);
    expect(summary).toEqual({
      count: 5,
      averageRoiBps: 2494,
      hotCount: 1,
      potentialMinor: 513000,
    });
  });
  it('does not call a losing or unvalued BUY a hot deal', () => {
    const item = demoOpportunities[1];
    expect(isHotDeal({ ...item, operatingProfitMinor: -100 })).toBe(false);
    expect(isHotDeal({ ...item, hasValuation: false })).toBe(false);
    expect(radarSummary([{ ...item, operatingProfitMinor: -100 }]).potentialMinor).toBe(
      0,
    );
  });
  it('preserves unknown values instead of treating missing estimates as zero', () => {
    expect(radarSummary([demoOpportunities[3]])).toEqual({
      count: 1,
      averageRoiBps: null,
      hotCount: 0,
      potentialMinor: null,
    });
    expect(radarSummary([])).toEqual({
      count: 0,
      averageRoiBps: null,
      hotCount: 0,
      potentialMinor: 0,
    });
  });
  it('does not present missing risk information as low risk', () => {
    expect(opportunityRisk({ ...demoOpportunities[1], topRisk: undefined }).label).toBe(
      'Ryzyko nieocenione',
    );
    expect(opportunityRisk(demoOpportunities[2]).tone).toBe('danger');
  });
  it('labels AI output only when an actual AI summary is available', () => {
    expect(opportunityInsight(demoOpportunities[1]).label).toBe('Sygnał z analizy');
    expect(
      opportunityInsight({ ...demoOpportunities[1], insight: 'Sprawdź stan GPU.' }),
    ).toEqual({ label: 'Insight AI', text: 'Sprawdź stan GPU.' });
  });
});
