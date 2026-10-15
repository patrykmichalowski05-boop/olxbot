import React, { useState } from "react";
import { Pressable, Switch, Text, View } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { ApiError, apiErrorMessage } from "@/api/errors";
import {
  deleteSearch,
  getSearches,
  getSourceHealth,
  saveSearch,
  searchPlatforms,
  type SavedSearch,
  type SearchPlatform,
} from "@/api/endpoints/searches";
import { AppScreen } from "@/components/AppScreen";
import { Badge } from "@/components/Badge";
import { ConfirmationSheet } from "@/components/ConfirmationSheet";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { Header } from "@/components/Header";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PrimaryButton } from "@/components/PrimaryButton";
import { useAuth } from "@/features/auth/AuthContext";
import { useTheme } from "@/theme/ThemeProvider";
import { layout } from "@/theme/tokens";
import { formatMoneyMinor, parseMoneyInput } from "@/utils/money";

const names: Record<SearchPlatform, string> = {
  OLX: "OLX",
  FACEBOOK: "Facebook",
  ALLEGRO_LOKALNIE: "Allegro Lokalnie",
  OTOMOTO: "Otomoto",
  VINTED: "Vinted",
};

export default function SearchesScreen() {
  const { colors, spacing, typography, radii } = useTheme();
  const { mode, userId } = useAuth();
  const router = useRouter();
  const cache = useQueryClient();
  const [query, setQuery] = useState("");
  const [budget, setBudget] = useState("");
  const [profit, setProfit] = useState("300");
  const [roi, setRoi] = useState("20");
  const [shipping, setShipping] = useState("20");
  const [repairs, setRepairs] = useState("0");
  const [fee, setFee] = useState("0");
  const [reserve, setReserve] = useState("5");
  const [excluded, setExcluded] = useState("uszkodzony, pudełko, atrapa");
  const [purpose, setPurpose] = useState<"flip" | "cheap">("flip");
  const [category, setCategory] = useState<
    "ELECTRONICS" | "CAR" | "FASHION" | "OTHER"
  >("ELECTRONICS");
  const [platforms, setPlatforms] = useState<SearchPlatform[]>([
    "ALLEGRO_LOKALNIE",
  ]);
  const [saving, setSaving] = useState(false);
  const [editingSearch, setEditingSearch] = useState<SavedSearch | null>(null);
  const [pendingDelete, setPendingDelete] = useState<SavedSearch | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const enabled = mode === "live";
  const searches = useQuery({
    queryKey: ["saved-searches", userId],
    queryFn: ({ signal }) => getSearches(signal),
    enabled,
  });
  const health = useQuery({
    queryKey: ["source-health", userId],
    queryFn: ({ signal }) => getSourceHealth(signal),
    enabled,
    refetchInterval: 60000,
  });
  const panel = {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.xxl,
    backgroundColor: colors.surface,
    padding: spacing.section,
    gap: spacing.lg,
  };
  const refresh = async () => {
    await Promise.all([
      cache.invalidateQueries({ queryKey: ["saved-searches", userId] }),
      cache.invalidateQueries({ queryKey: ["source-health", userId] }),
    ]);
  };
  const numberInput = (minor: number | null | undefined) =>
    minor == null ? "" : String(minor / 100);

  const resetForm = () => {
    setEditingSearch(null);
    setQuery("");
    setBudget("");
    setProfit("300");
    setRoi("20");
    setShipping("20");
    setRepairs("0");
    setFee("0");
    setReserve("5");
    setExcluded("uszkodzony, pudełko, atrapa");
    setPurpose("flip");
    setCategory("ELECTRONICS");
    setPlatforms(["ALLEGRO_LOKALNIE"]);
  };

  const editSearch = (item: SavedSearch) => {
    setEditingSearch(item);
    setQuery(item.query);
    setBudget(numberInput(item.max_price_minor));
    setProfit(numberInput(item.min_profit_minor));
    setRoi(numberInput(item.min_roi_bps));
    setShipping(numberInput(item.costs.shipping_minor));
    setRepairs(numberInput(item.costs.repairs_minor));
    setFee(numberInput(item.costs.sale_fee_bps));
    setReserve(numberInput(item.costs.reserve_bps));
    setExcluded(item.excluded_terms.join(", "));
    setPurpose(item.purpose);
    setCategory(
      ["ELECTRONICS", "CAR", "FASHION", "OTHER"].includes(item.category)
        ? (item.category as "ELECTRONICS" | "CAR" | "FASHION" | "OTHER")
        : "OTHER",
    );
    setPlatforms([...item.platforms]);
    setError("");
    setMessage(
      `Edytujesz: ${item.name}. Przewiń do formularza na górze.`
    );
  };

  const removeSearch = async () => {
    if (!pendingDelete || saving) return;

    const id = pendingDelete.id;
    const name = pendingDelete.name;

    setSaving(true);
    setError("");

    try {
      await deleteSearch(id);

      if (editingSearch?.id === id) {
        resetForm();
      }

      setPendingDelete(null);
      setMessage(`Usunięto wyszukiwanie: ${name}`);

      await refresh();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (item: SavedSearch) => {
    setSaving(true);
    setError("");
    try {
      await saveSearch({ ...item, enabled: !item.enabled });
      await refresh();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };
  const submit = async () => {
    const limit = budget.trim() ? parseMoneyInput(budget) : null;
    const minProfit = parseMoneyInput(profit);
    const minRoi = parseMoneyInput(roi);
    const deliveryCost = parseMoneyInput(shipping);
    const repairCost = parseMoneyInput(repairs);
    const feeBps = parseMoneyInput(fee);
    const reserveBps = parseMoneyInput(reserve);
    if (
      query.trim().length < 3 ||
      !platforms.length ||
      (budget.trim() && limit === null) ||
      (purpose === "cheap" && !limit) ||
      minProfit === null ||
      minRoi === null ||
      minRoi > 100000 ||
      deliveryCost === null ||
      repairCost === null ||
      feeBps === null ||
      feeBps > 10000 ||
      reserveBps === null ||
      reserveBps > 10000
    ) {
      setError(
        "Podaj model, platformy i poprawne kwoty. Tryb limitu ceny wymaga budżetu.",
      );
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await saveSearch({
        ...(editingSearch ?? {}),
        id: editingSearch?.id ??
          `search-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: query.trim().slice(0, 120),
        query: query.trim(),
        platforms,
        purpose,
        category,
        max_price_minor: limit,
        min_profit_minor: minProfit,
        min_roi_bps: minRoi,
        excluded_terms: excluded
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        notify_initial: false,
        costs: {
          ...(editingSearch?.costs ?? {}),
          shipping_minor: deliveryCost,
          repairs_minor: repairCost,
          travel_minor: 0,
          other_minor: 0,
          sale_fee_bps: feeBps,
          reserve_bps: reserveBps,
        },
      });
      const wasEditing = editingSearch !== null;

      resetForm();

      setMessage(
        wasEditing
          ? "Zmiany zapisane. Zmiana filtrów może rozpocząć nową obserwację ofert."
          : "Wyszukiwanie zapisane. Nowe okazje pojawią się po sprawdzeniu źródeł.",
      );
      await refresh();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };
  const unavailable =
    searches.error instanceof ApiError && searches.error.status === 404;
  return (
    <AppScreen scroll>
      <View
        style={{
          width: "100%",
          maxWidth: layout.formMaxWidth,
          alignSelf: "center",
          gap: spacing.lg,
        }}
      >
        <Header
          title="Moje wyszukiwania"
          subtitle="Wybierz przedmiot i warunki dobrej ceny"
          showBack
          showNotifications={false}
        />
        {!enabled ? (
          <EmptyState
            icon="search-outline"
            title="Wyszukiwania na Twoim koncie"
            description="Zapisane modele i alerty są dostępne po połączeniu z usługą wyszukiwania."
            actionLabel="Wróć do radaru"
            onAction={() => router.back()}
          />
        ) : searches.isPending ? (
          <LoadingSkeleton rows={2} />
        ) : searches.isError ? (
          <ErrorState
            title={
              unavailable ? "Wyszukiwania nie są jeszcze dostępne" : undefined
            }
            message={
              unavailable
                ? "Usługa wyszukiwania nie jest jeszcze włączona dla tego połączenia."
                : apiErrorMessage(searches.error)
            }
            onRetry={() => {
              void searches.refetch();
            }}
          />
        ) : (
          <>
            <View style={panel}>
              <Text style={[typography.headline, { color: colors.text }]}>
                {editingSearch ? "Edytujesz wyszukiwanie" : "Czego szukasz?"}
              </Text>
              <FormField
                label="Dokładny model i wariant"
                placeholder="np. RTX 4070 12GB lub iPhone 14 128GB"
                value={query}
                onChangeText={setQuery}
                maxLength={150}
              />
              <Text
                style={[
                  typography.caption,
                  { color: colors.textMuted },
                ]}
              >
                Domyślnie zaznaczono Allegro Lokalnie.
                Pozostałe platformy wymagają weryfikacji integracji.
              </Text>
              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  gap: spacing.sm,
                }}
              >
                {searchPlatforms.map((platform) => (
                  <Pressable
                    key={platform}
                    accessibilityRole="checkbox"
                    accessibilityState={{
                      checked: platforms.includes(platform),
                    }}
                    accessibilityLabel={names[platform]}
                    onPress={() =>
                      setPlatforms((current) =>
                        current.includes(platform)
                          ? current.filter((p) => p !== platform)
                          : [...current, platform],
                      )
                    }
                    style={{
                      minHeight: 44,
                      padding: spacing.md,
                      borderRadius: radii.pill,
                      backgroundColor: platforms.includes(platform)
                        ? colors.accentBg
                        : colors.surfaceElevated,
                    }}
                  >
                    <Text
                      style={[
                        typography.bodyStrong,
                        {
                          color: platforms.includes(platform)
                            ? colors.accent
                            : colors.textMuted,
                        },
                      ]}
                    >
                      {names[platform]}
                    </Text>
                  </Pressable>
                ))}
              </View>
              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  gap: spacing.sm,
                }}
              >
                {(
                  [
                    { id: "ELECTRONICS", label: "Elektronika" },
                    { id: "CAR", label: "Auta" },
                    { id: "FASHION", label: "Moda" },
                    { id: "OTHER", label: "Pozostałe" },
                  ] as const
                ).map((item) => (
                  <PrimaryButton
                    key={item.id}
                    label={item.label}
                    variant={category === item.id ? "primary" : "secondary"}
                    onPress={() => setCategory(item.id)}
                  />
                ))}
              </View>
              <View
                style={{
                  flexDirection: "row",
                  gap: spacing.sm,
                  flexWrap: "wrap",
                }}
              >
                {(
                  [
                    { value: "flip", label: "Potencjał zysku" },
                    { value: "cheap", label: "Limit ceny" },
                  ] as const
                ).map((item) => (
                  <PrimaryButton
                    key={item.value}
                    label={item.label}
                    variant={purpose === item.value ? "primary" : "secondary"}
                    onPress={() => setPurpose(item.value)}
                  />
                ))}
              </View>
              <FormField
                label="Maksymalna cena (zł)"
                placeholder="np. 1500"
                keyboardType="decimal-pad"
                value={budget}
                onChangeText={setBudget}
              />
              {purpose === "flip" ? (
                <>
                  <Text
                    style={[typography.caption, { color: colors.textMuted }]}
                  >
                    Prognoza wymaga rozpoznanego modelu i pełnych cech wariantu.
                    Jeśli brakuje danych porównawczych, możesz obserwować
                    przedmiot w trybie limitu ceny.
                  </Text>
                  <FormField
                    label="Minimalny wynik po kosztach (zł)"
                    keyboardType="decimal-pad"
                    value={profit}
                    onChangeText={setProfit}
                  />
                  <FormField
                    label="Minimalny ROI (%)"
                    keyboardType="decimal-pad"
                    value={roi}
                    onChangeText={setRoi}
                  />
                  <FormField
                    label="Wysyłka i odbiór (zł)"
                    keyboardType="decimal-pad"
                    value={shipping}
                    onChangeText={setShipping}
                  />
                  <FormField
                    label="Przewidywane naprawy (zł)"
                    keyboardType="decimal-pad"
                    value={repairs}
                    onChangeText={setRepairs}
                  />
                  <FormField
                    label="Prowizja od sprzedaży (%)"
                    keyboardType="decimal-pad"
                    value={fee}
                    onChangeText={setFee}
                  />
                  <FormField
                    label="Rezerwa od ceny zakupu (%)"
                    keyboardType="decimal-pad"
                    value={reserve}
                    onChangeText={setReserve}
                  />
                </>
              ) : null}
              <FormField
                label="Pomiń słowa, oddzielone przecinkiem"
                value={excluded}
                onChangeText={setExcluded}
                maxLength={600}
              />
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                Pierwsze sprawdzenie tworzy punkt odniesienia. Alerty obejmują
                kolejne nowe oferty i spadki cen. Wycena wymaga porównywalnych
                wariantów; wynik jest prognozą przed podatkiem. Powiadomienia
                Telegram wymagają aktywnej konfiguracji na Twoim koncie.
              </Text>
              <PrimaryButton
                label={editingSearch ? "Zapisz zmiany" : "Zapisz wyszukiwanie"}
                icon={editingSearch ? "save-outline" : "add-outline"}
                loading={saving}
                onPress={() => {
                  void submit();
                }}
              />
              {editingSearch ? (
                <PrimaryButton
                  label="Anuluj edycję"
                  variant="secondary"
                  disabled={saving}
                  onPress={() => {
                    resetForm();
                    setMessage("");
                  }}
                />
              ) : null}
            </View>
            {searches.data?.length ? (
              searches.data.map((item) => (
                <View key={item.id} style={panel}>
                  <View
                    style={{
                      flexDirection: "row",
                      alignItems: "center",
                      gap: spacing.md,
                    }}
                  >
                    <View style={{ flex: 1 }}>
                      <Text
                        style={[typography.headline, { color: colors.text }]}
                      >
                        {item.name}
                      </Text>
                      <Text
                        style={[
                          typography.caption,
                          { color: colors.textMuted },
                        ]}
                      >
                        {item.platforms.map((p) => names[p]).join(" · ")}
                      </Text>
                    </View>
                    <Switch
                      accessibilityLabel={`Aktywne wyszukiwanie ${item.name}`}
                      value={item.enabled}
                      disabled={saving}
                      onValueChange={() => {
                        void toggle(item);
                      }}
                      trackColor={{ true: colors.accentMuted }}
                    />
                  </View>
                  <Badge
                    label={
                      item.purpose === "cheap"
                        ? `Do ${formatMoneyMinor(item.max_price_minor)}`
                        : `Wynik od ${formatMoneyMinor(item.min_profit_minor)}`
                    }
                    tone={item.enabled ? "accent" : "neutral"}
                  />
                  <View
                    style={{
                      flexDirection: "row",
                      flexWrap: "wrap",
                      gap: spacing.sm,
                    }}
                  >
                    <PrimaryButton
                      label="Edytuj"
                      variant="secondary"
                      disabled={saving}
                      onPress={() => editSearch(item)}
                    />
                    <PrimaryButton
                      label="Usuń"
                      variant="ghost"
                      disabled={saving}
                      onPress={() => setPendingDelete(item)}
                    />
                  </View>
                  {health.data?.items
                    .filter((row) => row.search_id === item.id)
                    .map((row) => (
                      <Text
                        key={row.platform}
                        style={[
                          typography.caption,
                          {
                            color:
                              row.status === "OK"
                                ? colors.textMuted
                                : colors.warning,
                          },
                        ]}
                      >
                        {names[row.platform]} ·{" "}
                        {row.status === "OK"
                          ? `${row.count} ofert sprawdzonych`
                          : "Sprawdzanie źródła wstrzymane"}
                      </Text>
                    ))}
                </View>
              ))
            ) : (
              <EmptyState
                title="Dodaj pierwsze wyszukiwanie"
                description="Zapisz konkretny model, aby radar wiedział, jakie okazje Cię interesują."
              />
            )}
            {health.isError ? (
              <Text style={[typography.caption, { color: colors.warning }]}>
                Nie udało się odświeżyć stanu źródeł.
              </Text>
            ) : null}
          </>
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
      <ConfirmationSheet
        visible={pendingDelete !== null}
        title="Usunąć wyszukiwanie?"
        description={
          pendingDelete
            ? `Usuniesz profil „${pendingDelete.name}”, jego wyniki w radarze i oczekujące alerty. Tej operacji nie można cofnąć.`
            : ""
        }
        confirmLabel="Usuń wyszukiwanie"
        onConfirm={() => {
          void removeSearch();
        }}
        onCancel={() => {
          if (!saving) setPendingDelete(null);
        }}
        loading={saving}
      />
    </AppScreen>
  );
}
