export type InboxEvent = {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type NotificationView = {
  id: string;
  category: string;
  title: string;
  reason: string;
  at: string;
};

export type NotificationsPage = {
  items: NotificationView[];
  nextBeforeId: string | null;
};

function money(minor: unknown): string | null {
  if (typeof minor !== 'number' || !Number.isSafeInteger(minor) || minor < 0) {
    return null;
  }
  return `${(minor / 100).toFixed(2)} zł`;
}

function reference(value: unknown): string {
  return typeof value === 'string' && value.trim() ? value : 'brak identyfikatora';
}

export function mapInboxEvent(event: InboxEvent): NotificationView {
  const data = event.payload ?? {};
  const from = money(data.from_minor);
  const to = money(data.to_minor);
  const target = money(data.target_minor);
  const listing = reference(data.listing_id);
  const deal = reference(data.deal_id);

  let category = 'Zdarzenie';
  let title = 'Nowe zdarzenie';
  let reason = event.event_type;

  switch (event.event_type) {
    case 'LISTING_PRICE_DROP':
      category = 'Cena';
      title = 'Obniżka ceny oferty';
      reason = `${from ?? '—'} → ${to ?? '—'} · Oferta ${listing}`;
      break;
    case 'WATCH_TARGET_REACHED':
      category = 'Obserwowane';
      title = 'Cena osiągnęła próg';
      reason = `Nowa cena: ${to ?? '—'} · Próg: ${target ?? '—'} · Oferta ${listing}`;
      break;
    case 'DEAL_PURCHASED':
      category = 'Flip';
      title = 'Zarejestrowano zakup';
      reason = `Transakcja ${deal}`;
      break;
    case 'DEAL_COST_ADDED':
      category = 'Flip';
      title = 'Dodano koszt';
      reason = `Transakcja ${deal}`;
      break;
    case 'DEAL_SOLD':
      category = 'Flip';
      title = 'Zarejestrowano sprzedaż';
      reason = `Transakcja ${deal}`;
      break;
  }

  return { id: event.id, category, title, reason, at: event.created_at };
}
