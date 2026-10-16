import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { FormField } from "@/components/FormField";
import { PrimaryButton } from "@/components/PrimaryButton";
import { SelectField } from "@/components/SelectField";
import type { RadarFilters } from "@/features/radar/filterStore";
import { useTheme } from "@/theme/ThemeProvider";
import { parseMoneyInput } from "@/utils/money";
import { useWorkspaceLayout } from "./layout";

export function RadarToolbar({
  value,
  onApply,
  onClear,
}: {
  value: RadarFilters;
  onApply: (value: RadarFilters) => void;
  onClear: () => void;
}) {
  const { colors, typography, radii } = useTheme();
  const { narrow } = useWorkspaceLayout();
  const [query, setQuery] = useState(value.query);
  const [platform, setPlatform] = useState(
    value.platforms.length === 1
      ? value.platforms[0]
      : value.platforms.length > 1
        ? "MULTI"
        : "ALL",
  );
  const [minimum, setMinimum] = useState(
    value.minBudgetMinor == null ? "" : String(value.minBudgetMinor / 100),
  );
  const [maximum, setMaximum] = useState(
    value.maxBudgetMinor === null ? "" : String(value.maxBudgetMinor / 100),
  );
  const [sort, setSort] = useState(value.sort);
  const [error, setError] = useState("");
  const submit = () => {
    const min = minimum.trim() ? parseMoneyInput(minimum) : null;
    const max = maximum.trim() ? parseMoneyInput(maximum) : null;
    if (
      (minimum.trim() && min === null) ||
      (maximum.trim() && max === null) ||
      (min !== null && max !== null && min > max)
    ) {
      setError(
        "Podaj poprawny zakres cen. Cena „od” nie może być wyższa niż cena „do”.",
      );
      return;
    }
    setError("");
    onApply({
      ...value,
      query: query.trim().slice(0, 120),
      platforms:
        platform === "MULTI"
          ? value.platforms
          : platform === "ALL"
            ? []
            : [platform],
      minBudgetMinor: min,
      maxBudgetMinor: max,
      sort,
    });
  };
  return (
    <View
      style={{
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radii.xl,
        backgroundColor: colors.navigation,
        padding: 20,
        gap: 14,
      }}
    >
      <View
        style={{
          flexDirection: "row",
          flexWrap: "wrap",
          alignItems: "flex-end",
          gap: 12,
        }}
      >
        <View
          style={{ flexBasis: narrow ? "100%" : 240, flexGrow: 2, minWidth: 0 }}
        >
          <FormField
            compact
            label="Czego szukasz?"
            placeholder="np. RTX 4060, laptop do gier"
            value={query}
            onChangeText={setQuery}
            maxLength={120}
            returnKeyType="search"
            onSubmitEditing={submit}
          />
        </View>
        <View
          style={{ flexBasis: narrow ? "100%" : 125, flexGrow: 1, minWidth: 0 }}
        >
          <SelectField
            label="Platforma"
            value={platform}
            onChange={setPlatform}
            options={[
              {
                value: "ALL",
                label: "Wszystkie",
              },
              ...(value.platforms.length > 1
                ? [{ value: "MULTI", label: "Wybrane platformy" }]
                : []),
              { value: "OLX", label: "OLX" },
              { value: "FACEBOOK", label: "Facebook" },
              { value: "ALLEGRO_LOKALNIE", label: "Allegro Lokalnie" },
              { value: "OTOMOTO", label: "Otomoto" },
              { value: "VINTED", label: "Vinted" },
            ]}
          />
        </View>
        <View
          style={{ flexBasis: narrow ? "44%" : 110, flexGrow: 1, minWidth: 0 }}
        >
          <FormField
            compact
            label="Cena od (zł)"
            placeholder="0"
            keyboardType="decimal-pad"
            value={minimum}
            onChangeText={setMinimum}
            maxLength={16}
            returnKeyType="search"
            onSubmitEditing={submit}
          />
        </View>
        <View
          style={{ flexBasis: narrow ? "44%" : 110, flexGrow: 1, minWidth: 0 }}
        >
          <FormField
            compact
            label="Cena do (zł)"
            placeholder="bez limitu"
            keyboardType="decimal-pad"
            value={maximum}
            onChangeText={setMaximum}
            maxLength={16}
            returnKeyType="search"
            onSubmitEditing={submit}
          />
        </View>
        <View
          style={{ flexBasis: narrow ? "100%" : 145, flexGrow: 1, minWidth: 0 }}
        >
          <SelectField
            label="Sortowanie"
            value={sort}
            onChange={setSort}
            options={[
              { value: "fresh", label: "Najnowsze" },
              { value: "price", label: "Najniższa cena" },
              { value: "profit", label: "Najwyższy wynik" },
              { value: "roi", label: "Najwyższy ROI" },
              { value: "quality", label: "Z wyceną" },
            ]}
          />
        </View>
        <View
          style={{
            flexDirection: "row",
            gap: 8,
            flexBasis: narrow ? "100%" : "auto",
          }}
        >
          <PrimaryButton
            label="Wyczyść"
            variant="secondary"
            onPress={onClear}
            style={narrow ? { flex: 1 } : undefined}
          />
          <PrimaryButton
            label="Szukaj"
            onPress={submit}
            style={narrow ? { flex: 1 } : undefined}
          />
        </View>
      </View>
      {error ? (
        <Text
          accessibilityLiveRegion="polite"
          style={[typography.caption, { color: colors.loss }]}
        >
          {error}
        </Text>
      ) : null}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Text style={[typography.caption, { color: colors.textMuted }]}>
          Szybko:
        </Text>
        {["RTX 4070", "RTX 5060", "Ryzen", "PC gaming"].map((preset) => (
          <Pressable
            key={preset}
            accessibilityRole="button"
            onPress={() =>
              onApply({
                ...value,
                query: preset === "PC gaming" ? "komputer gamingowy" : preset,
              })
            }
            style={({ pressed }) => ({
              minHeight: 34,
              justifyContent: "center",
              paddingHorizontal: 12,
              borderWidth: 1,
              borderColor: colors.accentMuted,
              borderRadius: 20,
              backgroundColor: colors.surface,
              opacity: pressed ? 0.65 : 1,
            })}
          >
            <Text
              style={[
                typography.caption,
                { color: colors.textMuted, fontWeight: "600" },
              ]}
            >
              {preset}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}
