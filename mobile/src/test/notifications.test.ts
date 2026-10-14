import { mapInboxEvent } from '@/api/mappers/notification';

describe('PostgreSQL notification mapper', () => {
  it('formats real price drop fields from API', () => {
    const result = mapInboxEvent({
      id: 'e1', event_type: 'LISTING_PRICE_DROP',
      payload: { listing_id: 'l1', from_minor: 120000, to_minor: 99000 },
      created_at: '2026-10-14T10:00:00+00:00',
    });
    expect(result.reason).toContain('1200.00 zł');
    expect(result.reason).toContain('990.00 zł');
    expect(result.reason).toContain('l1');
  });

  it('recognizes price target event', () => {
    const result = mapInboxEvent({
      id: 'e2', event_type: 'WATCH_TARGET_REACHED',
      payload: { listing_id: 'l2', to_minor: 99000, target_minor: 100000 },
      created_at: '2026-10-14T10:00:00+00:00',
    });
    expect(result.title).toBe('Cena osiągnęła próg');
    expect(result.reason).toContain('1000.00 zł');
  });

  it('does not fabricate unread state', () => {
    const result = mapInboxEvent({
      id: 'e3', event_type: 'DEAL_SOLD',
      payload: { deal_id: 'd1' },
      created_at: '2026-10-14T10:00:00+00:00',
    });
    expect(result.title).toBe('Zarejestrowano sprzedaż');
    expect(result).not.toHaveProperty('read');
  });
});
