# Flip Hunter - etapy 62-66

62. Composite PostgreSQL foreign key:
    ochrona przed przypisaniem transakcji do oferty
    z innego workspace.

63. Outbox:
    zapis autora oraz czasu zdarzenia finansowego.

64. API:
    historia finansowa konkretnej transakcji.

65. PostgreSQL:
    testy rownoleglych zakupow i sprzedazy.

66. API:
    endpoint diagnostyczny /api/v2/healthz.

Migracje:
- 0003_deal_workspace_fk
- 0004_outbox_audit

Nowy endpoint:

GET /api/v2/workspaces/{workspace_id}/deals/{deal_id}/events

Healthcheck:

GET /api/v2/healthz

UWAGA:
Migracje uruchamia GitHub Actions na bazie testowej.

Nie uruchamiaj migracji na produkcji.
Nie zmieniaj /opt/olx-bot.
Nie restartuj systemd.

To nadal backend developerski.
