import { ApiError, apiErrorMessage } from '@/api/errors';

describe('User-facing errors', () => {
  it.each([400, 401, 403, 404, 409, 422, 429, 500, 503])(
    'hides raw details for status %s',
    (status) => {
      const message = apiErrorMessage(
        new ApiError(status, `API HTTP ${status}`, {
          detail: 'SQL traceback EXPO_PUBLIC_FLIP_WORKSPACE_ID',
        }),
      );
      expect(message).not.toMatch(/API|HTTP|SQL|traceback|EXPO_PUBLIC|500|503/);
      expect(message.length).toBeGreaterThan(20);
    },
  );
  it('hides configuration errors in plain Error instances and unknown responses', () => {
    expect(
      apiErrorMessage(new Error('Brak EXPO_PUBLIC_FLIP_WORKSPACE_ID')),
    ).not.toContain('EXPO_PUBLIC');
    expect(apiErrorMessage({ token: 'private' })).not.toContain('private');
  });
  it('explains interrupted network requests', () => {
    expect(apiErrorMessage(new TypeError('Failed to fetch'))).toContain(
      'Sprawdź internet',
    );
  });
});
