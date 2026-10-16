# Etap 72: odpornosc przetwarzania outbox

Test PostgreSQL sprawdza: niewazny token leasingu, czasowe niepowodzenie,
ponowne pobranie, odrzucenie starego leasingu, jednokrotne utworzenie
powiadomienia oraz izolacje skrzynek roznych workspace.

Test uruchamia GitHub Actions na bazie flip_test. Na produkcji nie
uruchamiamy Redis, Celery, beat, migracji ani dodatkowego workera.
Powiadomienia pozostaja wewnetrzne, bez wysylki na Telegram lub push.
