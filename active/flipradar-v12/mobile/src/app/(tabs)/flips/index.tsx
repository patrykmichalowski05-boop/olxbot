import React, { useMemo } from "react";
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import { AppScreen } from "@/components/AppScreen";
import { Badge } from "@/components/Badge";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Header } from "@/components/Header";
import { IconButton } from "@/components/IconButton";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { MoneyValue } from "@/components/MoneyValue";
import { PrimaryButton } from "@/components/PrimaryButton";
import { StatCard } from "@/components/StatCard";
import { useTheme } from "@/theme/ThemeProvider";
import { workspaceId } from "@/utils/config";
import { formatMoneyMinor } from "@/utils/money";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { useAuth } from "@/features/auth/AuthContext";

const statusLabels: Record<string, string> = {
  BOUGHT: "Kupiony",
  PURCHASED: "Kupiony",
  LISTED: "W sprzedaży",
  SOLD: "Sprzedany",
  CANCELLED: "Anulowany",
  ARCHIVED: "Archiwum",
};
export default function FlipsScreen() {
  const router = useRouter();
  const { pagePadding } = useWorkspaceLayout();
  const { userId } = useAuth();
  const { colors, spacing, typography, radii } = useTheme();
  const available = api.mode === "demo" || Boolean(workspaceId());
  const dealsQuery = useQuery({
    queryKey: ["deals", api.mode, userId],
    queryFn: () => api.deals.list(),
    enabled: available,
  });
  const items = useMemo(() => dealsQuery.data?.items ?? [], [dealsQuery.data]);
  const stats = useMemo(() => {
    const sold = items.filter((item) => item.status === "SOLD");
    const open = items.filter((item) =>
      ["BOUGHT", "PURCHASED", "LISTED"].includes(item.status),
    );
    return {
      sold: sold.length,
      open: open.length,
      profit: sold.reduce(
        (sum, item) => sum + (item.realized_profit_minor ?? 0),
        0,
      ),
      capital: open.reduce(
        (sum, item) => sum + item.purchase_minor + item.cost_minor,
        0,
      ),
    };
  }, [items]);
  const known = Boolean(dealsQuery.data);
  return (
    <AppScreen padded={false} bottomInset={false}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{
          paddingHorizontal: pagePadding,
          paddingBottom: spacing.lg,
          gap: spacing.md,
          flexGrow: 1,
        }}
        refreshControl={
          available ? (
            <RefreshControl
              refreshing={dealsQuery.isRefetching}
              onRefresh={() => {
                void dealsQuery.refetch();
              }}
              tintColor={colors.accent}
              colors={[colors.accent]}
            />
          ) : undefined
        }
        ListHeaderComponent={
          <View style={{ gap: spacing.lg, marginBottom: spacing.sm }}>
            <View>
              <Header
                title="Moje flipy"
                subtitle="Od pierwszego zakupu do wyniku."
                rightSlot={
                  <IconButton
                    icon="stats-chart-outline"
                    label="Analityka flipów"
                    onPress={() => router.push("/analytics")}
                  />
                }
                showNotifications={false}
              />
              <DemoBanner />
            </View>
            <View
              style={[
                styles.analytics,
                {
                  backgroundColor: colors.surface,
                  borderColor: colors.border,
                  borderRadius: radii.xxl,
                  padding: spacing.lg,
                },
              ]}
            >
              <View style={styles.sectionRow}>
                <Text style={[typography.label, { color: colors.textMuted }]}>
                  TWÓJ PORTFEL
                </Text>
                <Ionicons
                  name="pulse-outline"
                  size={18}
                  color={colors.accent}
                />
              </View>
              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  gap: spacing.sm,
                }}
              >
                <StatCard
                  label="Zrealizowany wynik"
                  icon="trending-up-outline"
                  value={known ? formatMoneyMinor(stats.profit) : "—"}
                  accent
                />
                <StatCard
                  label="Zaangażowany kapitał"
                  icon="wallet-outline"
                  value={known ? formatMoneyMinor(stats.capital) : "—"}
                />
                <StatCard
                  label="Aktywne flipy"
                  icon="briefcase-outline"
                  value={known ? String(stats.open) : "—"}
                />
                <StatCard
                  label="Sprzedane"
                  icon="checkmark-circle-outline"
                  value={known ? String(stats.sold) : "—"}
                />
              </View>
              <Text style={[typography.caption, { color: colors.textSubtle }]}>
                {known
                  ? "Podsumowanie pobranych flipów (do 30). Kapitał obejmuje zakup i koszty aktywnych pozycji."
                  : "Po zapisaniu pierwszego flipa zobaczysz tutaj kapitał, koszty i wyniki sprzedaży."}
              </Text>
            </View>
            {dealsQuery.isRefetchError && dealsQuery.data ? (
              <ErrorState
                message="Nie udało się odświeżyć portfela. Widzisz ostatnio pobrane dane."
                onRetry={() => {
                  void dealsQuery.refetch();
                }}
                retrying={dealsQuery.isFetching}
              />
            ) : null}
            <Text style={[typography.headline, { color: colors.text }]}>
              Twoje transakcje
            </Text>
          </View>
        }
        ListEmptyComponent={
          dealsQuery.isError && dealsQuery.data ? null : available &&
            dealsQuery.isPending ? (
            <LoadingSkeleton rows={2} />
          ) : available && dealsQuery.isError ? (
            <ErrorState
              message={apiErrorMessage(dealsQuery.error)}
              onRetry={() => {
                void dealsQuery.refetch();
              }}
              retrying={dealsQuery.isFetching}
            />
          ) : (
            <View style={{ gap: spacing.md }}>
              <EmptyState
                icon="briefcase-outline"
                title="Nie masz jeszcze zapisanych flipów"
                description="Znajdź okazję, sprawdź wycenę i zapisz zakup ze szczegółów oferty. Tutaj prześledzisz cały wynik transakcji."
                actionLabel="Przejdź do radaru"
                onAction={() => router.push("/radar")}
              />
              <PrimaryButton
                label="Przeanalizuj własną ofertę"
                variant="ghost"
                icon="scan-outline"
                onPress={() => router.push("/analyze")}
              />
            </View>
          )
        }
        renderItem={({ item }) => (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Szczegóły flipa: ${item.title ?? "Zakupiony przedmiot"}`}
            onPress={() =>
              router.push({
                pathname: "/flips/[dealId]",
                params: { dealId: item.id },
              })
            }
            style={({ pressed }) => [
              styles.card,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
                borderRadius: radii.xxl,
                padding: spacing.lg,
                gap: spacing.lg,
                opacity: pressed ? 0.7 : 1,
              },
            ]}
          >
            <View style={styles.sectionRow}>
              <View style={{ flex: 1, gap: spacing.sm }}>
                <Badge
                  label={statusLabels[item.status] ?? "W trakcie"}
                  tone={item.status === "SOLD" ? "success" : "accent"}
                />
                <Text
                  style={[typography.bodyStrong, { color: colors.text }]}
                  numberOfLines={2}
                >
                  {item.title ?? "Zakupiony przedmiot"}
                </Text>
              </View>
              <Ionicons name="arrow-forward" size={20} color={colors.accent} />
            </View>
            <View style={styles.row}>
              <MoneyValue label="Zakup" amountMinor={item.purchase_minor} />
              <MoneyValue label="Koszty" amountMinor={item.cost_minor} />
              <MoneyValue
                label="Zrealizowany wynik"
                amountMinor={
                  item.status === "SOLD" ? item.realized_profit_minor : null
                }
                emptyLabel="Po sprzedaży"
              />
            </View>
          </Pressable>
        )}
      />
    </AppScreen>
  );
}
const styles = StyleSheet.create({
  card: { borderWidth: 1 },
  analytics: { borderWidth: 1, gap: 16 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 16 },
  sectionRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
});
