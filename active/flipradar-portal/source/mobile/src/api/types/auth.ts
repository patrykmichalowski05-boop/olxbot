export type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

export type MeResponse = {
  user_id: string;
  access?: string;
};
