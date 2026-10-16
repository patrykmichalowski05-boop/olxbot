import React, { useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Switch,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getSearches,
  getSourceHealth,
  saveSearch,
  searchPlatforms,
  type SavedSearch,
  type SearchPlatform,
} from "@/api/endpoints/searches";
import { getAccount } from "@/api/endpoints/portal";
import { ApiError, apiErrorMessage } from "@/api/errors";
import { AccountAccessBoundary } from "@/features/portal/AccountAccessBoundary";
import { AppScreen } from "@/components/AppScreen";
import { Badge } from "@/components/Badge";
import { DemoBanner } from "@/components/DemoBanner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { Header } from "@/components/Header";
import { IconButton } from "@/components/IconButton";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PrimaryButton } from "@/components/PrimaryButton";
import { SelectField } from "@/components/SelectField";
import { useAuth } from "@/features/auth/AuthContext";
import { demoSearches } from "@/features/workspace/demoSearches";
import { useWorkspaceLayout } from "@/features/workspace/layout";
import { platformName, priceLabel } from "@/features/workspace/presentation";
import { WorkspaceNotice } from "@/features/workspace/WorkspaceNotice";
import { useTheme } from "@/theme/ThemeProvider";
import { portalEnabled } from "@/utils/config";
import { formatUserDateTime } from "@/utils/datetime";
import { parseMoneyInput } from "@/utils/money";

function SearchesContent() {
  const { colors, typography, radii } = useTheme();
  const { mode, userId, ready, signedIn } = useAuth();
  const { narrow } = useWorkspaceLayout();
  const params = useLocalSearchParams<{ query?: string }>();
  const router = useRouter();
  const cache = useQueryClient();
  const [formOpen, setFormOpen] = useState(Boolean(params.query));
  const [query, setQuery] = useState(
    typeof params.query === "string" ? params.query.slice(0, 120) : "",
  );
  const [budget, setBudget] = useState("");
  const [profit, setProfit] = useState("300");
  const [roi, setRoi] = useState("20");
  const [shipping, setShipping] = useState("20");
  const [repairs, setRepairs] = useState("0");
  const [fee, setFee] = useState("0");
  const [reserve, setReserve] = useState("5");
  const [excluded, setExcluded] = useState("uszkodzony, pudełko, atrapa");
  const [purpose, setPurpose] = useState<"flip" | "cheap">("flip");
  const [category, setCategory] = useState("ELECTRONICS");
  const [platforms, setPlatforms] = useState<SearchPlatform[]>([
    "OLX",
  ]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const attempt = useRef<{ fingerprint: string; id: string } | null>(null);
  const enabled = ready && signedIn;
  const searches = useQuery({
    queryKey: ["saved-searches", userId, mode],
    queryFn: ({ signal }) =>
      mode === "demo" ? demoSearches.list() : getSearches(signal),
    enabled,
  });
  const health = useQuery({
    queryKey: ["source-health", userId],
    queryFn: ({ signal }) => getSourceHealth(signal),
    enabled: enabled && mode === "live",
    refetchInterval: 60000,
  });
  const account = useQuery({
    queryKey: ["portal-account", userId],
    queryFn: ({ signal }) => getAccount(signal),
    enabled: enabled && mode === "live" && portalEnabled(),
  });
  const refresh = () =>
    Promise.all([
      cache.invalidateQueries({ queryKey: ["saved-searches", userId] }),
      cache.invalidateQueries({ queryKey: ["source-health", userId] }),
      cache.invalidateQueries({ queryKey: ["portal-account", userId] }),
    ]);
  const toggle = useMutation({
    mutationFn: (item: SavedSearch) =>
      mode === "demo"
        ? demoSearches.save({ ...item, enabled: !item.enabled })
        : saveSearch({ ...item, enabled: !item.enabled }),
    onSuccess: () => {
      setError("");
      void refresh();
    },
    onError: (error) => setError(apiErrorMessage(error)),
  });
  const submit = async () => {
    const limit = budget.trim() ? parseMoneyInput(budget) : null;
    const minProfit = parseMoneyInput(profit);
    const minRoi = parseMoneyInput(roi);
    const delivery = parseMoneyInput(shipping);
    const repair = parseMoneyInput(repairs);
    const saleFee = parseMoneyInput(fee);
    const safety = parseMoneyInput(reserve);
    if (
      query.trim().length < 3 ||
      !platforms.length ||
      (budget.trim() && limit === null) ||
      (purpose === "cheap" && !limit) ||
      minProfit === null ||
      minRoi === null ||
      minRoi > 100000 ||
      delivery === null ||
      repair === null ||
      saleFee === null ||
      saleFee > 10000 ||
      safety === null ||
      safety > 10000
    ) {
      setError(
        "Podaj model, co najmniej jedną platformę i poprawne kwoty. Tryb limitu ceny wymaga budżetu.",
      );
      return;
    }
    const body = {
      name: query.trim(),
      query: query.trim(),
      platforms,
      purpose,
      category,
      max_price_minor: limit,
      min_profit_minor: minProfit,
      min_roi_bps: minRoi,
      enabled: true,
      excluded_terms: excluded
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
      notify_initial: false,
      costs: {
        shipping_minor: delivery,
        repairs_minor: repair,
        travel_minor: 0,
        other_minor: 0,
        sale_fee_bps: saleFee,
        reserve_bps: safety,
      },
    };
    const fingerprint = JSON.stringify(body);
    if (!attempt.current || attempt.current.fingerprint !== fingerprint)
      attempt.current = {
        fingerprint,
        id: `search-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      };
    setSaving(true);
    setError("");
    try {
      const profile = { ...body, id: attempt.current.id };
      if (mode === "demo") await demoSearches.save(profile);
      else await saveSearch(profile);
      attempt.current = null;
      setFormOpen(false);
      setQuery("");
      setMessage(
        mode === "demo"
          ? "Przykładowe wyszukiwanie zapisane w podglądzie. Nie uruchamia pobierania ofert."
          : "Wyszukiwanie zapisane. Wyniki pojawią się po sprawdzeniu źródeł.",
      );
      await refresh();
    } catch (error) {
      setError(apiErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };
  const quotaUsed = account.data && !account.data.access.can_search;
  const panel = {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.xl,
    padding: narrow ? 20 : 24,
    backgroundColor: colors.surface,
    gap: 16,
  };
  return (
    <AppScreen scroll>
      <Header
        title="Moje wyszukiwania"
        subtitle="Wybrane modele, warunki dobrej ceny i Twoje alerty"
        rightSlot={
          <IconButton
            label="Dodaj wyszukiwanie"
            icon="add-outline"
            onPress={() => {
              setError("");
              setFormOpen(true);
            }}
          />
        }
      />
      <View style={{ gap: 20 }}>
        <DemoBanner />
        {mode === "live" ? (
          <WorkspaceNotice text="Aktualny skaner obsługuje indywidualne wyszukiwania OLX. Fraza, kategoria i limit ceny działają. Koszty, ROI i prognoza zysku nie filtrują jeszcze skanera V9." />
        ) : null}
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <View style={{ gap: 4 }}>
            <Text style={[typography.headline, { color: colors.text }]}>
              Twoje zapisane modele
            </Text>
            <Text style={[typography.body, { color: colors.textMuted }]}>
              {searches.data
                ? `${searches.data.length} wyszukiwań · ${searches.data.filter((item) => item.enabled).length} aktywnych`
                : "Wczytujemy Twoją listę"}
            </Text>
          </View>
          <PrimaryButton
            label="Nowe wyszukiwanie"
            icon="add-outline"
            onPress={() => {
              setError("");
              setFormOpen(true);
            }}
          />
        </View>
        {message ? (
          <WorkspaceNotice text={message} onDismiss={() => setMessage("")} />
        ) : null}
        {quotaUsed ? (
          <WorkspaceNotice text="Twój pakiet nie pozwala teraz dodać kolejnego wyszukiwania. Szczegóły dostępu sprawdzisz na swoim koncie." />
        ) : null}
        {searches.isPending ? (
          <LoadingSkeleton rows={3} compact />
        ) : searches.isError ? (
          <ErrorState
            title={
              searches.error instanceof ApiError &&
              searches.error.status === 404
                ? "Wyszukiwania nie są jeszcze dostępne"
                : "Nie udało się wczytać wyszukiwań"
            }
            message={apiErrorMessage(searches.error)}
            onRetry={() => {
              void searches.refetch();
            }}
          />
        ) : !searches.data.length ? (
          <EmptyState
            icon="search-outline"
            title="Dodaj pierwsze wyszukiwanie"
            description="Wybierz dokładny model, platformy i budżet. Radar będzie zbierał pasujące oferty na Twoim koncie."
            actionLabel="Dodaj wyszukiwanie"
            onAction={() => setFormOpen(true)}
          />
        ) : (
          searches.data.map((item) => {
            const rows =
              health.data?.items.filter((row) => row.search_id === item.id) ??
              [];
            const last = rows
              .map((row) => row.checked_at)
              .filter((value) => Number.isFinite(Date.parse(value)))
              .sort((a, b) => Date.parse(b) - Date.parse(a))[0];
            return (
              <View key={item.id} style={panel}>
                <View
                  style={{
                    flexDirection: "row",
                    alignItems: "flex-start",
                    gap: 12,
                  }}
                >
                  <View style={{ flex: 1, gap: 10 }}>
                    <Text style={[typography.headline, { color: colors.text }]}>
                      {item.name}
                    </Text>
                    <View
                      style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}
                    >
                      {item.platforms.map((platform) => (
                        <Badge
                          key={platform}
                          label={platformName(platform)}
                          tone={platform === "FACEBOOK" ? "accent" : "neutral"}
                        />
                      ))}
                      <Badge
                        label={item.enabled ? "Aktywne" : "Wstrzymane"}
                        tone={item.enabled ? "success" : "neutral"}
                      />
                    </View>
                  </View>
                  <Switch
                    accessibilityLabel={`Aktywne wyszukiwanie: ${item.name}`}
                    value={item.enabled}
                    disabled={toggle.isPending || saving}
                    onValueChange={() => toggle.mutate(item)}
                    trackColor={{ true: colors.accentMuted }}
                    thumbColor={colors.surface}
                  />
                </View>
                <View
                  style={{ flexDirection: "row", flexWrap: "wrap", gap: 20 }}
                >
                  <Text style={[typography.body, { color: colors.textMuted }]}>
                    {item.purpose === "cheap"
                      ? `Budżet: do ${priceLabel(item.max_price_minor)}`
                      : `Wynik od ${priceLabel(item.min_profit_minor)} · ROI od ${item.min_roi_bps / 100}%`}
                  </Text>
                  <Text
                    style={[typography.caption, { color: colors.textMuted }]}
                  >
                    Ostatni skan:{" "}
                    {mode === "demo" ? "przykład" : formatUserDateTime(last)}
                  </Text>
                </View>
                {rows.some((row) => row.status !== "OK") ? (
                  <Text style={[typography.caption, { color: colors.warning }]}>
                    Część źródeł czeka na ponowne sprawdzenie. Dostępne wyniki
                    pozostają w radarze.
                  </Text>
                ) : null}
                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: 10,
                  }}
                >
                  <Text
                    style={[
                      typography.caption,
                      { color: colors.textSubtle, alignSelf: "center" },
                    ]}
                  >
                    {item.enabled
                      ? "Nowe oferty pojawią się po kolejnym skanie."
                      : "Włącz wyszukiwanie, aby zbierać kolejne oferty."}
                  </Text>
                  <PrimaryButton
                    label="Zobacz wyniki"
                    variant="secondary"
                    icon="arrow-forward"
                    onPress={() =>
                      router.push({
                        pathname: "/searches/results",
                        params: { id: item.id },
                      })
                    }
                  />
                </View>
              </View>
            );
          })
        )}
        {error && !formOpen ? <ErrorState message={error} /> : null}
        {health.isError ? (
          <ErrorState
            title="Status źródeł jest chwilowo niedostępny"
            message="Wyszukiwania pozostają zapisane. Spróbuj odświeżyć status za chwilę."
            onRetry={() => {
              void health.refetch();
            }}
          />
        ) : null}
        {account.data ? (
          <PrimaryButton
            label={`${account.data.plan.name} · pozostało ${account.data.access.remaining ?? "bez limitu"} wyszukiwań · Moje konto`}
            variant="ghost"
            onPress={() => router.push("/account")}
          />
        ) : null}
      </View>
      <Modal
        visible={formOpen}
        transparent
        animationType="fade"
        onRequestClose={() => {
          if (!saving) setFormOpen(false);
        }}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={{
            flex: 1,
            backgroundColor: colors.overlay,
            justifyContent: "center",
            padding: narrow ? 12 : 32,
          }}
        >
          <View
            accessibilityViewIsModal
            style={{
              width: "100%",
              maxWidth: 820,
              maxHeight: "94%",
              alignSelf: "center",
              backgroundColor: colors.surface,
              borderRadius: radii.xl,
              borderWidth: 1,
              borderColor: colors.border,
              overflow: "hidden",
            }}
          >
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                padding: 20,
                borderBottomWidth: 1,
                borderColor: colors.border,
                gap: 12,
              }}
            >
              <View style={{ flex: 1 }}>
                <Text style={[typography.headline, { color: colors.text }]}>
                  Nowe wyszukiwanie
                </Text>
                <Text style={[typography.caption, { color: colors.textMuted }]}>
                  Zapisz model i określ, kiedy oferta jest dla Ciebie dobra.
                </Text>
              </View>
              <IconButton
                label="Zamknij formularz"
                icon="close-outline"
                disabled={saving}
                onPress={() => setFormOpen(false)}
              />
            </View>
            <ScrollView
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={{ padding: 20, gap: 16 }}
            >
              <FormField
                compact
                label="Dokładny model i wariant"
                placeholder="np. RTX 4070 12GB lub iPhone 14 128GB"
                value={query}
                onChangeText={setQuery}
                maxLength={120}
              />
              <View style={{ gap: 8 }}>
                <Text
                  style={[
                    typography.caption,
                    { color: colors.textMuted, fontWeight: "600" },
                  ]}
                >
                  Platformy
                </Text>
                <View
                  style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}
                >
                  {searchPlatforms.map((platform) => (
                    <Pressable
                      key={platform}
                      accessibilityRole="checkbox"
                      accessibilityState={{
                        checked: platforms.includes(platform),
                      }}
                      onPress={() =>
                        setPlatforms((old) =>
                          old.includes(platform)
                            ? old.filter((p) => p !== platform)
                            : [...old, platform],
                        )
                      }
                      style={{
                        minHeight: 38,
                        paddingHorizontal: 12,
                        paddingVertical: 9,
                        borderWidth: 1,
                        borderColor: platforms.includes(platform)
                          ? colors.accentMuted
                          : colors.border,
                        borderRadius: radii.md,
                        backgroundColor: platforms.includes(platform)
                          ? colors.accentBg
                          : colors.surface,
                      }}
                    >
                      <Text
                        style={[
                          typography.body,
                          {
                            color: platforms.includes(platform)
                              ? colors.accent
                              : colors.textMuted,
                          },
                        ]}
                      >
                        {platformName(platform)}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
                <View
                  style={{ flexBasis: narrow ? "100%" : "46%", flexGrow: 1 }}
                >
                  <SelectField
                    label="Kategoria"
                    value={category}
                    onChange={setCategory}
                    options={[
                      { value: "ELECTRONICS", label: "Elektronika" },
                      { value: "CAR", label: "Auta" },
                      { value: "FASHION", label: "Moda" },
                      { value: "OTHER", label: "Pozostałe" },
                    ]}
                  />
                </View>
                <View
                  style={{ flexBasis: narrow ? "100%" : "46%", flexGrow: 1 }}
                >
                  <SelectField
                    label="Cel wyszukiwania"
                    value={purpose}
                    onChange={setPurpose}
                    options={[
                      { value: "flip", label: "Potencjał zysku" },
                      { value: "cheap", label: "Limit ceny" },
                    ]}
                  />
                </View>
              </View>
              <FormField
                compact
                label="Maksymalna cena zakupu (zł)"
                placeholder={purpose === "cheap" ? "np. 1500" : "bez limitu"}
                keyboardType="decimal-pad"
                value={budget}
                onChangeText={setBudget}
                maxLength={16}
              />
              {purpose === "flip" ? (
                <View
                  style={{
                    backgroundColor: colors.navigation,
                    borderWidth: 1,
                    borderColor: colors.border,
                    borderRadius: radii.lg,
                    padding: 16,
                    gap: 14,
                  }}
                >
                  <Text style={[typography.bodyStrong, { color: colors.text }]}>
                    Zysk i koszty
                  </Text>
                  <View
                    style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}
                  >
                    {[
                      {
                        label: "Minimalny wynik (zł)",
                        value: profit,
                        change: setProfit,
                      },
                      {
                        label: "Minimalny ROI (%)",
                        value: roi,
                        change: setRoi,
                      },
                      {
                        label: "Wysyłka i odbiór (zł)",
                        value: shipping,
                        change: setShipping,
                      },
                      {
                        label: "Naprawy (zł)",
                        value: repairs,
                        change: setRepairs,
                      },
                      {
                        label: "Prowizja sprzedaży (%)",
                        value: fee,
                        change: setFee,
                      },
                      {
                        label: "Rezerwa od zakupu (%)",
                        value: reserve,
                        change: setReserve,
                      },
                    ].map((field) => (
                      <View
                        key={field.label}
                        style={{
                          flexBasis: narrow ? "100%" : "46%",
                          flexGrow: 1,
                        }}
                      >
                        <FormField
                          compact
                          label={field.label}
                          value={field.value}
                          onChangeText={field.change}
                          keyboardType="decimal-pad"
                          maxLength={16}
                        />
                      </View>
                    ))}
                  </View>
                  <Text
                    style={[typography.caption, { color: colors.textMuted }]}
                  >
                    Prognoza wymaga porównywalnego modelu i wariantu. Przy braku
                    danych użyj limitu ceny.
                  </Text>
                </View>
              ) : null}
              <FormField
                compact
                label="Pomiń słowa (oddziel przecinkiem)"
                value={excluded}
                onChangeText={setExcluded}
                maxLength={600}
              />
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                Pierwszy skan tworzy punkt odniesienia. Kolejne nowe oferty i
                spadki cen mogą generować alerty zgodnie z Twoim pakietem. Nowy
                model wykorzystuje jedno wyszukiwanie.
              </Text>
              {mode === "demo" ? (
                <WorkspaceNotice text="Tryb demo: zapis działa wyłącznie w tym podglądzie i nie zużywa rzeczywistego pakietu." />
              ) : null}
              {error ? <ErrorState message={error} /> : null}
              {quotaUsed ? (
                <PrimaryButton
                  label="Sprawdź pakiet na swoim koncie"
                  onPress={() => {
                    setFormOpen(false);
                    router.push("/account");
                  }}
                />
              ) : (
                <PrimaryButton
                  label="Zapisz wyszukiwanie"
                  icon="add-outline"
                  loading={saving}
                  onPress={() => {
                    void submit();
                  }}
                />
              )}
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </AppScreen>
  );
}

export default function SearchesScreen() {
  return (
    <AccountAccessBoundary>
      <SearchesContent />
    </AccountAccessBoundary>
  );
}
