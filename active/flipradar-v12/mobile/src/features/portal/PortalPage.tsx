import React, { useState } from "react";
import { Text, View } from "react-native";
import { Redirect, useRouter } from "expo-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/AuthContext";
import { getAccount, requestPlan } from "@/api/endpoints/portal";
import { apiErrorMessage } from "@/api/errors";
import { AppScreen } from "@/components/AppScreen";
import { Header } from "@/components/Header";
import { Badge } from "@/components/Badge";
import { PrimaryButton } from "@/components/PrimaryButton";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { useTheme } from "@/theme/ThemeProvider";
import { portalEnabled } from "@/utils/config";
import type { PortalPageProps } from "./types";

export default function PortalPage({ page }: PortalPageProps) {
  const auth = useAuth();
  const router = useRouter();
  const cache = useQueryClient();
  const { colors, spacing, typography, radii } = useTheme();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const live = auth.mode === "live" && portalEnabled();
  const account = useQuery({
    queryKey: ["portal-account", auth.userId],
    queryFn: ({ signal }) => getAccount(signal),
    enabled: live && auth.signedIn,
    retry: 1,
  });
  if (page === "landing") return <Redirect href="/radar" />;
  if (page === "login" || page === "register")
    return <Redirect href="/login" />;
  if (!auth.ready || (live && account.isPending))
    return (
      <AppScreen>
        <LoadingSkeleton rows={2} />
      </AppScreen>
    );
  if (page === "bot" && (!live || account.data?.access.can_open_bot))
    return <Redirect href="/radar" />;
  return (
    <AppScreen scroll>
      <Header title="Twoje konto" showBack />
      <View style={{ gap: spacing.lg }}>
        {account.isError ? (
          <ErrorState
            message={apiErrorMessage(account.error)}
            onRetry={() => {
              void account.refetch();
            }}
          />
        ) : (
          <View
            style={{
              gap: spacing.lg,
              padding: spacing.section,
              borderRadius: radii.xxl,
              backgroundColor: colors.surface,
              borderWidth: 1,
              borderColor: colors.border,
            }}
          >
            <Text style={[typography.headline, { color: colors.text }]}>
              {account.data?.username ?? "Konto demonstracyjne"}
            </Text>
            <Badge
              label={account.data?.plan.name ?? "Podgląd aplikacji"}
              tone="accent"
            />
            <Text style={[typography.body, { color: colors.textMuted }]}>
              {account.data
                ? `Pozostałe wyszukiwania: ${account.data.access.remaining ?? "bez limitu"}`
                : "To podgląd interfejsu. Konto jest dostępne po połączeniu z usługą."}
            </Text>
            {account.data && !account.data.access.can_open_bot ? (
              <Text style={[typography.body, { color: colors.warning }]}>
                Dostęp jest nieaktywny. Zgłoś aktywację pakietu poniżej.
              </Text>
            ) : (
              <PrimaryButton
                label="Przejdź do bota"
                onPress={() => router.push("/radar")}
              />
            )}
            {live
              ? (["STANDARD", "PLUS"] as const).map((plan) => (
                  <PrimaryButton
                    key={plan}
                    label={`Zgłoś pakiet ${plan === "STANDARD" ? "Standard" : "Plus"}`}
                    variant="secondary"
                    disabled={busy}
                    onPress={async () => {
                      setBusy(true);
                      setError("");
                      try {
                        await requestPlan(plan);
                        await cache.invalidateQueries({
                          queryKey: ["portal-account", auth.userId],
                        });
                        setMessage(
                          "Zgłoszenie zapisane. Pakiet zmieni się po aktywacji przez operatora.",
                        );
                      } catch (e) {
                        setError(apiErrorMessage(e));
                      } finally {
                        setBusy(false);
                      }
                    }}
                  />
                ))
              : null}
            <PrimaryButton
              label="Strona główna"
              variant="secondary"
              onPress={() => router.push("/")}
            />
            <PrimaryButton
              label="Wyloguj się"
              variant="ghost"
              onPress={async () => {
                try {
                  await auth.logout();
                } catch (e) {
                  setError(apiErrorMessage(e));
                }
              }}
            />
          </View>
        )}
        {message ? (
          <Text
            accessibilityLiveRegion="polite"
            style={[typography.body, { color: colors.success }]}
          >
            {message}
          </Text>
        ) : null}
        {error ? <ErrorState message={error} /> : null}
      </View>
    </AppScreen>
  );
}
