import React from "react";
import { Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import { AppScreen } from "@/components/AppScreen";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Header } from "@/components/Header";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PrimaryButton } from "@/components/PrimaryButton";
import { RiskList } from "@/components/RiskList";
import { SourceStatus } from "@/components/SourceStatus";
import { useAuth } from "@/features/auth/AuthContext";
import { useWatchActions } from "@/features/workspace/hooks";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { MetricTile } from "@/features/workspace/MarketSummary";
import { OfferAnalysisCard } from "@/features/workspace/OfferAnalysisCard";
import { priceLabel } from "@/features/workspace/presentation";
import { WorkspaceNotice } from "@/features/workspace/WorkspaceNotice";
import { useRuntimeCapabilities } from "@/features/runtime/useRuntimeCapabilities";
import { useTheme } from "@/theme/ThemeProvider";
import { formatUserDateTime } from "@/utils/datetime";
import { workspaceId } from "@/utils/config";

export default function OfferDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { ready, signedIn, userId } = useAuth();
  const router = useRouter();
  const { colors, typography, radii } = useTheme();
  const { narrow } = useWorkspaceLayout();
  const detail = useQuery({
    queryKey: ["offer", id, api.mode, userId],
    enabled: Boolean(id) && ready && signedIn,
    queryFn: () => api.opportunityDetail(String(id)),
  });
  const watch = useWatchActions();
  const runtime = useRuntimeCapabilities();
  const item = detail.data;
  const panel = {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.xl,
    backgroundColor: colors.surface,
    padding: narrow ? 20 : 24,
    gap: 16,
  };
  return (
    <AppScreen scroll>
      <Header title="Szczegóły oferty" showBack backLabel="Wróć do wyników" />
      <View style={{ gap: 20 }}>
        <DemoBanner />
        {detail.isPending ? (
          <LoadingSkeleton rows={2} />
        ) : detail.isError ? (
          <ErrorState
            message={apiErrorMessage(detail.error)}
            onRetry={() => {
              void detail.refetch();
            }}
          />
        ) : !item ? (
          <EmptyState
            icon="document-outline"
            title="Ta oferta nie jest już dostępna"
            description="Ogłoszenie mogło wygasnąć lub zostać usunięte. Sprawdź pozostałe wyniki na swoim radarze."
            actionLabel="Przejdź do radaru"
            onAction={() => router.replace("/radar")}
          />
        ) : (
          <>
            <OfferAnalysisCard
              item={item}
              demo={api.mode === "demo"}
              defaultExpanded
              onWatch={watch.available ? () => watch.toggle(item) : undefined}
              watched={watch.isWatched(item)}
              watchLoading={watch.mutation.isPending}
              watchDisabled={
                !watch.writable ||
                watch.mutation.isPending ||
                watch.saved.isError ||
                watch.saved.isPending
              }
            />
            {watch.notice ? (
              <WorkspaceNotice
                text={watch.notice}
                onDismiss={watch.clearNotice}
              />
            ) : null}
            {watch.saved.isError ? (
              <ErrorState
                title="Zapisane oferty są chwilowo niedostępne"
                message="Możesz nadal sprawdzać szczegóły oferty."
                onRetry={() => {
                  void watch.saved.refetch();
                }}
              />
            ) : null}
            <View style={panel}>
              <Text style={[typography.headline, { color: colors.text }]}>
                Dane i koszty
              </Text>
              <SourceStatus
                platform={item.platform}
                status={item.sourceStatus}
              />
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
                {[
                  [
                    "Prognoza kosztów",
                    priceLabel(item.baseScenario?.costsMinor),
                  ],
                  ["Maksymalna cena zakupu", priceLabel(item.maxBuyMinor)],
                ].map(([label, value]) => (
                  <View
                    key={label}
                    style={{ flexBasis: narrow ? "100%" : "46%", flexGrow: 1 }}
                  >
                    <MetricTile label={label} value={value} />
                  </View>
                ))}
              </View>
              {item.specs.length ? (
                <View style={{ gap: 8 }}>
                  {item.specs.map((spec) => (
                    <View
                      key={spec.label}
                      style={{ flexDirection: "row", gap: 16 }}
                    >
                      <Text
                        style={[
                          typography.body,
                          { color: colors.textMuted, flex: 1 },
                        ]}
                      >
                        {spec.label}
                      </Text>
                      <Text
                        style={[typography.bodyStrong, { color: colors.text }]}
                      >
                        {spec.value}
                      </Text>
                    </View>
                  ))}
                </View>
              ) : null}
              <RiskList
                title="Co sprawdzić przed zakupem"
                items={item.risks}
                emptyLabel="Brak dodatkowej listy ryzyk w danych oferty"
              />
              <RiskList
                title="Brakujące informacje"
                items={item.unknowns}
                emptyLabel="Brak informacji o brakach w danych"
              />
            </View>
            {item.conservativeScenario && item.baseScenario ? (
              <View style={panel}>
                <Text style={[typography.headline, { color: colors.text }]}>
                  Scenariusze odsprzedaży
                </Text>
                <View
                  style={{ flexDirection: narrow ? "column" : "row", gap: 12 }}
                >
                  {[item.conservativeScenario, item.baseScenario].map(
                    (scenario) => (
                      <View
                        key={scenario.label}
                        style={{
                          flex: 1,
                          backgroundColor: colors.navigation,
                          padding: 16,
                          borderRadius: radii.lg,
                          gap: 10,
                        }}
                      >
                        <Text
                          style={[
                            typography.bodyStrong,
                            { color: colors.accent },
                          ]}
                        >
                          {scenario.label}
                        </Text>
                        {[
                          ["Zakup", scenario.purchaseMinor],
                          ["Odsprzedaż", scenario.resaleMinor],
                          ["Wynik po kosztach", scenario.profitMinor],
                        ].map(([label, amount]) => (
                          <View
                            key={String(label)}
                            style={{
                              flexDirection: "row",
                              justifyContent: "space-between",
                              gap: 12,
                            }}
                          >
                            <Text
                              style={[
                                typography.body,
                                { color: colors.textMuted },
                              ]}
                            >
                              {label}
                            </Text>
                            <Text
                              style={[
                                typography.bodyStrong,
                                { color: colors.text },
                              ]}
                            >
                              {priceLabel(
                                typeof amount === "number" ? amount : null,
                              )}
                            </Text>
                          </View>
                        ))}
                      </View>
                    ),
                  )}
                </View>
              </View>
            ) : null}
            {item.priceHistory.length > 1 ? (
              <View style={panel}>
                <Text style={[typography.headline, { color: colors.text }]}>
                  Historia ceny
                </Text>
                {item.priceHistory.map((point, index) => (
                  <View
                    key={`${point.at}-${index}`}
                    style={{
                      flexDirection: "row",
                      justifyContent: "space-between",
                      gap: 16,
                    }}
                  >
                    <Text
                      style={[typography.body, { color: colors.textMuted }]}
                    >
                      {formatUserDateTime(point.at)}
                    </Text>
                    <Text
                      style={[typography.bodyStrong, { color: colors.text }]}
                    >
                      {priceLabel(point.priceMinor)}
                    </Text>
                  </View>
                ))}
              </View>
            ) : null}
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
              {runtime.canWrite &&
              runtime.capabilities.deals &&
              item.listingId &&
              (api.mode === "demo" || workspaceId()) ? (
                <PrimaryButton
                  label="Zapisz zakup w moich flipach"
                  icon="briefcase-outline"
                  onPress={() =>
                    router.push({
                      pathname: "/purchase/[listingId]",
                      params: { listingId: String(item.listingId) },
                    })
                  }
                />
              ) : null}
              <PrimaryButton
                label="Przeanalizuj inną ofertę"
                variant="secondary"
                icon="scan-outline"
                onPress={() => router.push("/analyze")}
              />
            </View>
          </>
        )}
      </View>
    </AppScreen>
  );
}
