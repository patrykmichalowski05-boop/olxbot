import React, { useState } from "react";
import { Text, View } from "react-native";
import { useRouter } from "expo-router";
import { api } from "@/api";
import { apiErrorMessage } from "@/api/errors";
import { AccountAccessBoundary } from "@/features/portal/AccountAccessBoundary";
import { AppScreen } from "@/components/AppScreen";
import { Badge } from "@/components/Badge";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { Header } from "@/components/Header";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PrimaryButton } from "@/components/PrimaryButton";
import { useRadarOffers } from "@/features/workspace/hooks";
import { MetricTile, MarketSummary } from "@/features/workspace/MarketSummary";
import {
  confidenceLabel,
  hasUsableComparison,
  platformName,
  priceLabel,
} from "@/features/workspace/presentation";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { useTheme } from "@/theme/ThemeProvider";
import { radarSource } from "@/utils/config";

function MarketContent() {
  const { colors, typography, radii } = useTheme();
  const { narrow } = useWorkspaceLayout();
  const router = useRouter();
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const { items, request } = useRadarOffers(query);
  const valued = items.filter(hasUsableComparison);
  const search = () => setQuery(draft.trim().slice(0, 120));
  return (
    <AppScreen scroll>
      <Header
        title="Dane rynku"
        subtitle="Ceny i próby porównawcze dla ofert w Twoim radarze"
      />
      <View style={{ gap: 20 }}>
        <DemoBanner />
        <View
          style={{
            flexDirection: narrow ? "column" : "row",
            alignItems: "flex-end",
            gap: 12,
            backgroundColor: colors.navigation,
            borderRadius: radii.xl,
            padding: 20,
            borderWidth: 1,
            borderColor: colors.border,
          }}
        >
          <FormField
            compact
            containerStyle={{ flex: 1, alignSelf: "stretch" }}
            label="Model lub przedmiot"
            placeholder="np. RTX 4070 12GB"
            value={draft}
            onChangeText={setDraft}
            maxLength={120}
            returnKeyType="search"
            onSubmitEditing={search}
          />
          <View style={{ flexDirection: "row", gap: 8 }}>
            <PrimaryButton
              label="Wyczyść"
              variant="secondary"
              onPress={() => {
                setDraft("");
                setQuery("");
              }}
            />
            <PrimaryButton label="Sprawdź dane" onPress={search} />
          </View>
        </View>
        <MarketSummary
          items={items}
          title={
            query ? `Przegląd cen: ${query}` : "Przegląd cen wczytanych ofert"
          }
          loading={!request.data}
        />
        <Text style={[typography.headline, { color: colors.text }]}>
          Porównania dla ofert ({request.data ? valued.length : "—"})
        </Text>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          Każda próbka dotyczy modelu i wariantu danej oferty. Liczby porównań
          mogą obejmować te same ogłoszenia i nie są sumowane.
        </Text>
        {request.isRefetchError && request.data ? (
          <ErrorState
            message="Nie udało się odświeżyć danych rynku. Widzisz ostatnio pobrane wyniki."
            onRetry={() => {
              void request.refetch();
            }}
            retrying={request.isFetching}
          />
        ) : null}
        {request.isPending ? (
          <LoadingSkeleton rows={3} />
        ) : request.isError && !request.data ? (
          <ErrorState
            message={apiErrorMessage(request.error)}
            onRetry={() => {
              void request.refetch();
            }}
          />
        ) : !valued.length ? (
          <EmptyState
            icon="stats-chart-outline"
            title="Brakuje jeszcze danych porównawczych"
            description="Zapisz dokładny model i poczekaj na sprawdzenie źródeł. Bez porównywalnych ofert nie wyznaczamy wartości rynkowej."
            actionLabel="Moje wyszukiwania"
            onAction={() => router.push("/searches")}
          />
        ) : (
          valued.map((item) => (
            <View
              key={item.id}
              style={{
                backgroundColor: colors.surface,
                borderWidth: 1,
                borderColor: colors.border,
                borderRadius: radii.xl,
                padding: 20,
                gap: 14,
              }}
            >
              <View
                style={{
                  flexDirection: "row",
                  alignItems: "flex-start",
                  gap: 12,
                }}
              >
                <Text
                  style={[
                    typography.bodyStrong,
                    { color: colors.text, flex: 1 },
                  ]}
                >
                  {item.title}
                </Text>
                <Badge label={platformName(item.platform)} tone="accent" />
              </View>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
                {[
                  ["Mediana wariantu", priceLabel(item.market?.medianMinor)],
                  [
                    "Typowy zakres",
                    item.market?.lowMinor && item.market.highMinor
                      ? `${priceLabel(item.market.lowMinor).replace(" zł", "")}–${priceLabel(item.market.highMinor)}`
                      : "—",
                  ],
                  ["Porównania", String(item.market?.sampleCount ?? "—")],
                  ["Wiarygodność", confidenceLabel(item.market?.confidence)],
                ].map(([label, value]) => (
                  <View
                    key={label}
                    style={{ flexBasis: narrow ? "46%" : "22%", flexGrow: 1 }}
                  >
                    <MetricTile label={label} value={value} />
                  </View>
                ))}
              </View>
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 10,
                }}
              >
                <Text style={[typography.caption, { color: colors.textMuted }]}>
                  {item.market?.kind === "SOLD_VERIFIED"
                    ? "Potwierdzone ceny sprzedaży"
                    : "Ceny ofertowe · bez potwierdzenia transakcji"}
                </Text>
                {api.mode === "demo" ||
                radarSource() === "universal" ||
                item.listingId ? (
                  <PrimaryButton
                    label="Szczegóły oferty"
                    variant="secondary"
                    onPress={() =>
                      router.push({
                        pathname: "/offer/[id]",
                        params: {
                          id: item.listingId ? String(item.listingId) : item.id,
                        },
                      })
                    }
                  />
                ) : null}
              </View>
            </View>
          ))
        )}
        {request.isFetchNextPageError ? (
          <ErrorState
            message="Nie udało się pobrać kolejnej strony danych."
            onRetry={() => {
              void request.fetchNextPage();
            }}
          />
        ) : request.hasNextPage ? (
          <PrimaryButton
            label="Wczytaj więcej danych"
            loading={request.isFetchingNextPage}
            variant="secondary"
            onPress={() => {
              void request.fetchNextPage();
            }}
          />
        ) : null}
      </View>
    </AppScreen>
  );
}

export default function MarketScreen() {
  return (
    <AccountAccessBoundary>
      <MarketContent />
    </AccountAccessBoundary>
  );
}
