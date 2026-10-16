# Flip Hunter — etapy 52–56

52. Ograniczona pula polaczen PostgreSQL.
53. Weryfikacja tokenu i uprawnien workspace.
54. Blokada rekordu PostgreSQL przy sprzedazy.
55. API zakupu, kosztow, sprzedazy i podsumowania.
56. Testy HTTP z PostgreSQL w GitHub Actions.

## Uwagi

API /api/v1 jest zachowane przez istniejacy backend.

Nowe endpointy:

POST /api/v2/workspaces/{workspace_id}/deals
POST /api/v2/workspaces/{workspace_id}/deals/{deal_id}/costs
POST /api/v2/workspaces/{workspace_id}/deals/{deal_id}/sell
GET  /api/v2/workspaces/{workspace_id}/deals/{deal_id}

Operacje zapisu wymagaja:
- tokenu Bearer;
- przypisania do workspace;
- roli owner lub admin;
- naglowka Idempotency-Key.

Nie ma jeszcze endpointow zakladania kont/workspace.
Provisioning uzytkownikow i membership pozostaje do
kolejnego etapu.

Nie wdrazac publicznie bez dalszego audytu.

Nie instalowano PostgreSQL na Proxmox.
Nie uruchomiono nowego API na produkcji.
Nie zmieniono /opt/olx-bot.
