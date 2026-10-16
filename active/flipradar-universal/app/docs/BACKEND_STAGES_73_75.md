# Flip Hunter - etapy 73-75

73. Uniwersalny, autoryzowany import ofert:
    OLX, Vinted, Otomoto, MANUAL i inne zrodla.
    Historia cen, wersjonowanie, idempotentne zadania.

74. PostgreSQL radar:
    lista ofert, filtrowanie tytulu,
    ostatnia obserwacja, stabilna paginacja.
    Migracja Alembic: 0006_listing_created_at.

75. Test HTTP:
    nowa oferta, powtorzenie tego samego klucza,
    brak nowej rewizji przy identycznej cenie,
    zmiana ceny, izolacja workspace.

Endpointy:

POST /api/v2/workspaces/{workspace_id}/listings/ingest
GET /api/v2/workspaces/{workspace_id}/listings

To import reczny lub przez autoryzowana integracje.
Skrypt nie uruchamia scraperow ani nowych uslug.

Migracje PostgreSQL wykona GitHub Actions
na jednorazowym srodowisku testowym.

Produkcja /opt/olx-bot pozostaje bez zmian.
