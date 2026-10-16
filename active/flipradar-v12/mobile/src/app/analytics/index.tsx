import { RuntimeFeature } from "@/features/runtime/RuntimeFeature";
import React, { useMemo } from "react";
import { Text, View } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import { AppScreen } from "@/components/AppScreen";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Header } from "@/components/Header";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { StatCard } from "@/components/StatCard";
import { dealSummary } from "@/features/workspace/dealSummary";
import { useRuntimeCapabilities } from "@/features/runtime/useRuntimeCapabilities";
import { useTheme } from "@/theme/ThemeProvider";
import { workspaceId } from "@/utils/config";
import { formatMoneyMinor } from "@/utils/money";
import { useAuth } from "@/features/auth/AuthContext";

function AnalyticsScreenContent() {
  const router = useRouter();
  const runtime = useRuntimeCapabilities();
  const { userId } = useAuth();
  const { colors, spacing, typography } = useTheme();
  const available = api.mode === "demo" || Boolean(workspaceId());
  const dealsQuery = useQuery({
    queryKey: ["deals", api.mode, userId, "analytics"],
    queryFn: () => api.deals.list(),
    enabled: available,
  });
  const stats = useMemo(
    () => dealSummary(dealsQuery.data?.items ?? []),
    [dealsQuery.data],
  );
  return (
    <AppScreen scroll>
      <Header
        title={
          runtime.capabilities.backend === "flask-v12"
            ? "Analityka administratora"
            : "Analityka"
        }
        subtitle="Wyniki Twoich transakcji."
        showBack
        showNotifications={false}
      />
      <View style={{ gap: spacing.lg }}>
        {stats.incomplete ? (
          <Text style={[typography.body, { color: colors.warning }]}>
            Brakuje kompletnych kwot dla {stats.incomplete} pozycji. Niepełne
            sumy mają znak „—”.
          </Text>
        ) : null}
        <Text style={[typography.body, { color: colors.textMuted }]}>
          Podsumowanie pobranych flipów (do 30). Wynik obejmuje zakończone
          sprzedaże.
        </Text>
        {!available ? (
          <EmptyState
            title="Analityka czeka na pierwszego flipa"
            icon="stats-chart-outline"
            description="Po zapisaniu zakupów i sprzedaży pojawią się tutaj Twoje wyniki."
            actionLabel="Przejdź do radaru"
            onAction={() => router.push("/radar")}
          />
        ) : dealsQuery.isPending ? (
          <LoadingSkeleton rows={2} />
        ) : dealsQuery.isError ? (
          <ErrorState
            message={apiErrorMessage(dealsQuery.error)}
            onRetry={() => {
              void dealsQuery.refetch();
            }}
            retrying={dealsQuery.isFetching}
          />
        ) : (
          <View style={{ gap: spacing.md }}>
            <View
              style={{
                flexDirection: "row",
                flexWrap: "wrap",
                gap: spacing.sm,
              }}
            >
              <StatCard
                label="Zrealizowany wynik"
                value={formatMoneyMinor(stats.profit)}
                icon="trending-up-outline"
                accent
              />
              <StatCard
                label="Zakup aktywnych pozycji"
                value={formatMoneyMinor(stats.inventory)}
                icon="wallet-outline"
              />
              <StatCard
                label="Sprzedane przedmioty"
                value={String(stats.sold)}
                icon="checkmark-circle-outline"
              />
              <StatCard
                label="Koszty łącznie"
                value={formatMoneyMinor(stats.costs)}
                icon="receipt-outline"
              />
            </View>
            {!dealsQuery.data?.items.length ? (
              <EmptyState
                title="Brak transakcji do podsumowania"
                icon="stats-chart-outline"
                description="Zapisz pierwszy zakup ze szczegółów oferty, aby zacząć śledzić wyniki."
                actionLabel="Przejdź do radaru"
                onAction={() => router.push("/radar")}
              />
            ) : null}
          </View>
        )}
      </View>
    </AppScreen>
  );
}

export default function AnalyticsScreen() {
  return (
    <RuntimeFeature
      feature="deals_read"
      title="Analityka flipów"
      description="Statystyki transakcji znajdziesz w centrum narzędzi. Ten panel pokaże je po połączeniu historii z kontem."
      icon="stats-chart-outline"
    >
      <AnalyticsScreenContent />
    </RuntimeFeature>
  );
}
