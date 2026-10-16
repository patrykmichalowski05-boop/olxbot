import { createIdempotencyKey } from '@/utils/idempotency';

describe('createIdempotencyKey', () => {
  it('includes prefix and respects max length', () => {
    const key = createIdempotencyKey('purchase');
    expect(key.startsWith('purchase-')).toBe(true);
    expect(key.length).toBeLessThanOrEqual(128);
    expect(key.length).toBeGreaterThanOrEqual(8);
  });

  it('generates unique keys for new operations', () => {
    const a = createIdempotencyKey('sale');
    const b = createIdempotencyKey('sale');
    expect(a).not.toBe(b);
  });
});
