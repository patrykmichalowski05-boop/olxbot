# Mobile API — aktualny kontrakt developerski

- POST /api/v1/auth/login — logowanie.
- POST /api/v1/auth/refresh — rotacja sesji.
- POST /api/v1/auth/logout — wylogowanie.
- GET /api/v1/universal/mobile-radar — radar mobilny.
- POST /api/v1/universal/manual/analyze — ręczna analiza.
- GET/POST /api/v1/universal/watchlist — watchlista.
- POST /api/v1/universal/watchlist/close — zamknięcie.

Refresh token jest rotowany. Ponowne użycie starego
tokenu unieważnia powiązaną rodzinę sesji.

price_minor to cena żądana w ogłoszeniu, a nie
potwierdzona cena sprzedaży lub cena rynkowa.

NO_RELIABLE_VALUATION oznacza brak wiarygodnej
wyceny. Nie wolno przedstawiać takiej oferty jako
potwierdzonej okazji.

To API developerskie, nie pełny backend produkcyjny.
