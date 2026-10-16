# Flip Hunter - etapy 76-78

76. Obnizka ceny:
    LISTING_PRICE_DROP w transakcyjnym outbox.
    Zdarzenie powstaje tylko przy realnym spadku
    wzgledem poprzedniej obserwacji.

77. Historia cen:
    GET /api/v2/workspaces/{workspace_id}/listings/{listing_id}/history
    Rewizje, ceny i paginacja.
    Dostep ograniczony do workspace.

78. PostgreSQL + HTTP:
    Test spadku ceny 1200 -> 990 PLN,
    pojedynczego zdarzenia,
    dostarczenia do inbox i izolacji workspace.

Bez nowych scraperow i bez Telegrama.
Nie uruchamiamy Celery/beat ani uslug systemd.
Nie zmieniamy produkcji /opt/olx-bot.
