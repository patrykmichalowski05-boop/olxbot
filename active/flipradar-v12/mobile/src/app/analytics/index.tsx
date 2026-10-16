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
import { useTheme } from "@/theme/ThemeProvider";
import { workspaceId } from "@/utils/config";
import { formatMoneyMinor } from "@/utils/money";
import { useAuth } from "@/features/auth/AuthContext";

export default function AnalyticsScreen() {
  const router = useRouter();
  const { userId } = useAuth();
  const { colors, spacing, typography } = useTheme();
  const available = api.mode === "demo" || Boolean(workspaceId());
  const dealsQuery = useQuery({
    queryKey: ["deals", api.mode, userId, "analytics"],
    queryFn: () => api.deals.list(),
    enabled: available,
  });
  const stats = useMemo(() => {
    const items = dealsQuery.data?.items ?? [];
    const sold = items.filter((deal) => deal.status === "SOLD");
    const open = items.filter((deal) =>
      ["BOUGHT", "PURCHASED", "LISTED"].includes(deal.status),
    );
    return {
      sold: sold.length,
      profit: sold.reduce(
        (sum, deal) => sum + (deal.realized_profit_minor ?? 0),
        0,
      ),
      inventory: open.reduce((sum, deal) => sum + deal.purchase_minor, 0),
      costs: items.reduce((sum, deal) => sum + deal.cost_minor, 0),
    };
  }, [dealsQuery.data]);
  return (
    <AppScreen scroll>
      <Header
        title="Analityka"
        subtitle="Wyniki Twoich transakcji."
        showBack
        showNotifications={false}
      />
      <View style={{ gap: spacing.lg }}>
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
