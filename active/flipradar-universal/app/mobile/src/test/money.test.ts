import { formatMoneyMinor, parseMoneyInput } from '@/utils/money';

describe('parseMoneyInput', () => {
  it('parses comma decimals into minor units', () => {
    expect(parseMoneyInput('12,50')).toBe(1250);
  });

  it('parses dot decimals', () => {
    expect(parseMoneyInput('999.99')).toBe(99999);
  });

  it('rejects invalid strings', () => {
    expect(parseMoneyInput('12,5,5')).toBeNull();
    expect(parseMoneyInput('abc')).toBeNull();
  });
});

describe('formatMoneyMinor', () => {
  it('shows empty label when missing valuation', () => {
    expect(formatMoneyMinor(null, 'PLN', { emptyLabel: 'Brak wyceny' })).toBe(
      'Brak wyceny',
    );
  });
});
