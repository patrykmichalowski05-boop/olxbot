import { isPostgresUuid } from '@/utils/identifiers';

describe('Identyfikatory rejestru finansowego PostgreSQL', () => {
  it('odrzuca identyfikatory legacy i demo bez próby konwersji', () => {
    for (const id of ['501', 'snap-1001', 'listing:501', 'deal-demo-1', '', null, undefined]) expect(isPostgresUuid(id)).toBe(false);
  });
  it('zachowuje prawidłowy UUID jako ciąg znaków', () => {
    expect(isPostgresUuid('01e001ba-b0c0-4000-8000-000000000001')).toBe(true);
  });
});
