const PLN = 'PLN';

/** Parses user input with comma or dot decimal separator into minor units. */
export function parseMoneyInput(raw: string, currency = PLN): number | null {
  const trimmed = raw.trim().replace(/\s/g, '');
  if (!trimmed) {
    return null;
  }

  const normalized = trimmed.replace(',', '.');
  if (!/^\d+(\.\d{0,2})?$/.test(normalized)) {
    return null;
  }

  const [whole, frac = ''] = normalized.split('.');
  const padded = (frac + '00').slice(0, 2);
  const minor = Number(whole) * 100 + Number(padded);

  if (!Number.isSafeInteger(minor) || minor < 0) {
    return null;
  }

  if (currency !== PLN) {
    return minor;
  }

  return minor;
}

export function formatMoneyMinor(
  amountMinor: number | null | undefined,
  currency = PLN,
  options?: { emptyLabel?: string },
): string {
  if (amountMinor === null || amountMinor === undefined) {
    return options?.emptyLabel ?? 'Brak wyceny';
  }

  const major = amountMinor / 100;
  const formatted = major.toLocaleString('pl-PL', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (currency === PLN) {
    return `${formatted} zł`;
  }

  return `${formatted} ${currency}`;
}

export function formatRoiBps(roiBps: number | null | undefined): string {
  if (roiBps === null || roiBps === undefined) {
    return '—';
  }
  const pct = roiBps / 100;
  return `${pct.toFixed(1)}%`;
}

export function formatSignedMoneyMinor(amountMinor: number, currency = PLN): string {
  const sign = amountMinor > 0 ? '+' : amountMinor < 0 ? '−' : '';
  return `${sign}${formatMoneyMinor(Math.abs(amountMinor), currency)}`;
}
