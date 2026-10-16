# Flip Hunter — podetapy 57–61

57. Koszty zapisują outbox event w tej samej transakcji.
58. Właściciel workspace może odczytać faktyczne pozycje kosztowe.
59. Alembic 0002: data transakcji i kosztu, indeks chronologiczny.
60. Lista transakcji posortowana po czasie i ID z kursorem w SQL.
61. Testy HTTP PostgreSQL dla kosztów, list i izolacji workspace.

Ważne: cena ofertowa nie oznacza ceny transakcyjnej.
System nadal jest developerski, bez live skanerów i Celery/Redis.
Nie modyfikowano /opt/olx-bot ani systemd. Żadnych migracji
na produkcji; prawdziwa migracja odbywa się w GitHub Actions.

Endpointy developerskie:
GET /api/v2/workspaces/{workspace_id}/deals?limit=20&status=SOLD
GET /api/v2/workspaces/{workspace_id}/deals?before_id={last_id}
GET /api/v2/workspaces/{workspace_id}/deals/{deal_id}/costs

Sprawdź końcowy GitHub Actions postgres-integration. Skrypt lokalny
uruchamia jednostki i testy offline; testy PG na Ubuntu są pomijane.
