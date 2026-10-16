import type { RadarApiItem } from "@/api/types/radar";

export type PlanCode = "START" | "STANDARD" | "PLUS" | "LEGACY";
export type PortalPlan = {
  code: PlanCode;
  name: string;
  price_minor: number;
  searches: number | null;
  days: number | null;
  notifications: boolean;
  prices_are_examples: boolean;
};
export type Account = {
  user_id: string;
  username: string;
  role: "OWNER" | "MEMBER";
  plan: PortalPlan;
  access: {
    can_open_bot: boolean;
    can_search: boolean;
    can_receive_notifications: boolean;
    reason: string;
    remaining: number | null;
    limit: number | null;
    used: number;
    expires_at: string | null;
  };
  plan_request: { id: string; plan: PlanCode; status: string } | null;
};
export type PriceResult = {
  query: string;
  remaining: number | null;
  items: RadarApiItem[];
  example: boolean;
};
export type PublicConfig = {
  demo_data?: boolean;
  registration_enabled: boolean;
  public_search_available: boolean;
  payment_mode: string;
  plans: PortalPlan[];
};
export type AdminData = {
  accounts: {
    user_id: string;
    username: string;
    role: string;
    enabled: number;
    plan: PlanCode;
    used: number;
    expires_at: number | null;
  }[];
  requests: {
    id: string;
    user_id: string;
    username: string;
    plan: PlanCode;
    status: string;
  }[];
};
export type PortalPageProps = {
  page: "landing" | "login" | "register" | "account" | "bot" | "info";
};
