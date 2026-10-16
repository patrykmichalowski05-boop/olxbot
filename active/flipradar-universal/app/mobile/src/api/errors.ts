export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body: unknown = undefined) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401)
      return 'Sesja wygasła. Zaloguj się ponownie, aby kontynuować.';
    if (error.status === 403) return 'Ta funkcja nie jest dostępna dla Twojego konta.';
    if (error.status === 404)
      return 'Ten element nie jest już dostępny. Odśwież listę i spróbuj ponownie.';
    if (error.status === 409)
      return 'Dane uległy zmianie. Odśwież ekran przed ponownym zapisem.';
    if (error.status === 422 || error.status === 400)
      return 'Sprawdź wprowadzone dane i spróbuj ponownie.';
    if (error.status === 429)
      return 'Zbyt wiele prób w krótkim czasie. Spróbuj ponownie za chwilę.';
    if (error.status >= 500)
      return 'Usługa jest chwilowo niedostępna. Spróbuj ponownie za chwilę.';
    return 'Nie można teraz połączyć się z usługą. Sprawdź internet i spróbuj ponownie.';
  }
  if (error instanceof Error && /network|fetch|timeout|abort/i.test(error.message)) {
    return 'Połączenie zostało przerwane. Sprawdź internet i spróbuj ponownie.';
  }
  return 'Nie udało się wykonać tej operacji. Spróbuj ponownie za chwilę.';
}
