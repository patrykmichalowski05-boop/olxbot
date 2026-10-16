# Flip Hunter backend — etapy 47–51

47. Konfiguracja PostgreSQL.
48. Modele SQLAlchemy i izolacja workspace.
49. Migracja Alembic 0001.
50. Zakup, koszty, sprzedaz, idempotencja i outbox.
51. Integracyjne testy z PostgreSQL w GitHub Actions.

To fundament backendu, nie kompletne API produkcyjne.

Nie wykonano:
- migracji produkcyjnego SQLite;
- instalacji PostgreSQL na kontenerze OLX;
- uruchamiania Celery lub Redis;
- podlaczenia skanerow;
- wdrozenia produkcyjnego.

Test SQL offline:

FLIP_BACKEND_DATABASE_URL='postgresql+psycopg://test:pass@localhost/testdb' \
  python -m alembic -c backend/alembic.ini upgrade head --sql

Rzeczywisty test PostgreSQL uruchamia GitHub Actions.

Kolejne zmiany schematu wymagaja nowych migracji.
