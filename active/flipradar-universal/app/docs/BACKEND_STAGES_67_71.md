# Flip Hunter — etapy 67-71

67. Migracja 0005:
    outbox z leasingiem, licznikami prob,
    statusem DEAD i trwala skrzynka powiadomien.

68. Pobieranie zdarzen przez PostgreSQL
    FOR UPDATE SKIP LOCKED.
    Zapis powiadomienia i zatwierdzenie
    outbox w jednej transakcji.

69. Retry z backoffem, odzyskiwanie
    wygaslych leasingow, dead-letter.

70. Autoryzowane API:
    GET /api/v2/workspaces/{workspace_id}/notifications

71. Celery i Redis jako opcjonalny worker.
    Test integracyjny PostgreSQL w GitHub Actions.

UWAGA:
To sa powiadomienia wewnetrzne w bazie.
Brak wysylki Telegram, FCM, APNS.

Worker i beat NIE uruchamiaja sie automatycznie.
Zadna usluga systemd nie jest modyfikowana.
Nie ruszamy /opt/olx-bot.

Po przygotowaniu odrebnego srodowiska
developerskiego uruchomienie workera jest mozliwe
poleceniem:

celery -A backend.app.services.celery_tasks:app worker -l info

A harmonogramu:

celery -A backend.app.services.celery_tasks:app beat -l info

Nie uruchamiaj ich teraz na produkcji.
