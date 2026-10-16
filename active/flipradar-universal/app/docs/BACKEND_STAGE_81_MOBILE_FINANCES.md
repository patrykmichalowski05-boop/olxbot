# Etap 81 — prawdziwe dane finansowe FlipRadar

Backend:
- Lista transakcji zawiera title, cost_minor oraz realized_profit_minor.
- Szczegóły transakcji zawierają id, title, listing_id i currency.
- Koszty i zrealizowany zysk obliczane są na podstawie PostgreSQL.
- Niesprzedane przedmioty mają realized_profit_minor = null.

Mobile:
- GUI używa pól purchase_minor, cost_minor, sale_minor i realized_profit_minor.
- Dane demonstracyjne są mapowane osobno.
- Analityka obejmuje pierwszą stronę do 30 transakcji.
- Dodano testy TypeScript/Jest i test PostgreSQL.

Do zrobienia:
- Powiązać identyfikatory ofert starszego radaru v1 z UUID ofert API v2.
- Rozbudować analitykę o pełną paginację.

Produkcja /opt/olx-bot i panel WWW 8089 pozostają bez zmian.
