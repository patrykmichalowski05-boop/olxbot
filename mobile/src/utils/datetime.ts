export function formatUserDateTime(iso: string | null | undefined): string {
  if (!iso) {
    return '—';
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString('pl-PL', {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

export function formatRelativeSync(iso: string | null | undefined): string {
  if (!iso) {
    return 'nieznany';
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return 'przed chwilą';
  if (minutes < 60) return `${minutes} min temu`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h temu`;
  return formatUserDateTime(iso);
}
