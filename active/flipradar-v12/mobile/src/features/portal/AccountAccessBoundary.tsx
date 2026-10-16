import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useAuth } from "@/features/auth/AuthContext";
import { getAccount } from "@/api/endpoints/portal";
import { apiErrorMessage } from "@/api/errors";
import { portalEnabled } from "@/utils/config";
import { AppScreen } from "@/components/AppScreen";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";

export function AccountAccessBoundary({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userId, mode, signedIn } = useAuth();
  const router = useRouter();
  const enabled = mode === "live" && portalEnabled();
  const account = useQuery({
    queryKey: ["portal-account", userId],
    queryFn: ({ signal }) => getAccount(signal),
    enabled: enabled && signedIn,
    staleTime: 15000,
    refetchInterval: 60000,
  });
  if (!enabled) return <>{children}</>;
  if (account.isPending)
    return (
      <AppScreen>
        <LoadingSkeleton rows={2} />
      </AppScreen>
    );
  if (account.isError)
    return (
      <AppScreen>
        <ErrorState
          message={apiErrorMessage(account.error)}
          onRetry={() => {
            void account.refetch();
          }}
        />
      </AppScreen>
    );
  if (!account.data.access.can_open_bot)
    return (
      <AppScreen>
        <EmptyState
          icon="lock-closed-outline"
          title="Twój dostęp jest nieaktywny"
          description="Sprawdź pakiet i zgłoś aktywację na swoim koncie."
          actionLabel="Moje konto"
          onAction={() => router.push("/account")}
        />
      </AppScreen>
    );
  return <>{children}</>;
}
