import React, { useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { RadarFilters } from "@/features/radar/filterStore";
import { defaultFilters } from "@/features/radar/filterStore";
import { useTheme } from "@/theme/ThemeProvider";
import { CATEGORY_TABS } from "@/utils/labels";
import { parseMoneyInput } from "@/utils/money";
import { FormField } from "./FormField";
import { IconButton } from "./IconButton";
import { PrimaryButton } from "./PrimaryButton";
import { platformName } from "@/features/workspace/presentation";

type Props = {
  visible: boolean;
  initial: RadarFilters;
  onClose: () => void;
  onApply: (filters: RadarFilters) => void;
  onSaveProfile?: (name: string, filters: RadarFilters) => void;
};
const PLATFORMS = ["OLX", "FACEBOOK", "VINTED", "OTOMOTO", "ALLEGRO_LOKALNIE"];
const SORTS: { id: RadarFilters["sort"]; label: string }[] = [
  { id: "fresh", label: "Najnowsze" },
  { id: "profit", label: "Najwyższy wynik" },
  { id: "roi", label: "Najwyższy ROI" },
  { id: "price", label: "Najniższa cena" },
  { id: "quality", label: "Z wyceną" },
];
const inputAmount = (value: number | null) =>
  value === null ? "" : String(value / 100).replace(".", ",");
export function FilterSheet({
  visible,
  initial,
  onClose,
  onApply,
  onSaveProfile,
}: Props) {
  const { colors, spacing, typography, radii } = useTheme();
  const insets = useSafeAreaInsets();
  const { height } = useWindowDimensions();
  const [draft, setDraft] = useState(initial);
  const [budget, setBudget] = useState("");
  const [profit, setProfit] = useState("");
  const [roi, setRoi] = useState("");
  const [profileName, setProfileName] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const resetDraft = (next: RadarFilters) => {
    setDraft(next);
    setBudget(inputAmount(next.maxBudgetMinor));
    setProfit(inputAmount(next.minProfitMinor));
    setRoi(inputAmount(next.minRoiBps));
    setErrors({});
  };
  useEffect(() => {
    // Opening the modal intentionally restores the current filter snapshot.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (visible) resetDraft(initial);
  }, [visible, initial]);
  const validatedDraft = (): RadarFilters | null => {
    const nextErrors: Record<string, string> = {};
    const maxBudgetMinor = parseMoneyInput(budget);
    const minProfitMinor = parseMoneyInput(profit);
    const minRoiBps = parseMoneyInput(roi);
    if (budget.trim() && maxBudgetMinor === null)
      nextErrors.budget = "Podaj prawidłową kwotę, np. 1500,00.";
    if (profit.trim() && minProfitMinor === null)
      nextErrors.profit = "Podaj prawidłową kwotę, np. 400,00.";
    if (roi.trim() && minRoiBps === null)
      nextErrors.roi = "Podaj prawidłowy procent, np. 20,5.";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length
      ? null
      : { ...draft, maxBudgetMinor, minProfitMinor, minRoiBps };
  };
  const chip = (label: string, active: boolean, onPress: () => void) => (
    <Pressable
      key={label}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      aria-selected={active}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        {
          borderColor: active ? colors.accentMuted : colors.border,
          backgroundColor: active ? colors.accentBg : colors.background,
          borderRadius: radii.pill,
          opacity: pressed ? 0.65 : 1,
        },
      ]}
    >
      <Text
        style={[
          typography.caption,
          {
            color: active ? colors.accent : colors.textMuted,
            fontWeight: "600",
          },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
  return (
    <Modal
      visible={visible}
      transparent
      statusBarTranslucent
      animationType="fade"
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={[styles.overlay, { backgroundColor: colors.overlay }]}
      >
        <Pressable
          accessibilityLabel="Zamknij filtry"
          accessibilityRole="button"
          onPress={onClose}
          style={StyleSheet.absoluteFill}
        />
        <View
          accessibilityViewIsModal
          onAccessibilityEscape={onClose}
          style={[
            styles.sheet,
            {
              maxHeight: height - Math.max(insets.top, 24),
              backgroundColor: colors.surface,
              borderTopLeftRadius: radii.xxl,
              borderTopRightRadius: radii.xxl,
              borderColor: colors.border,
              paddingBottom: Math.max(insets.bottom, spacing.lg),
            },
          ]}
        >
          <View
            style={{
              width: 36,
              height: 4,
              borderRadius: 2,
              alignSelf: "center",
              backgroundColor: colors.border,
              marginTop: 8,
              marginBottom: 12,
            }}
          />
          <View style={[styles.header, { paddingHorizontal: spacing.section }]}>
            <View style={{ flex: 1 }}>
              <Text style={[typography.title, { color: colors.text }]}>
                Dopasuj radar
              </Text>
              <Text
                style={[
                  typography.caption,
                  { color: colors.textMuted, marginTop: 4 },
                ]}
              >
                Twoje kryteria. Trafniejsze okazje.
              </Text>
            </View>
            <IconButton icon="close" label="Zamknij filtry" onPress={onClose} />
          </View>
          <ScrollView
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{
              padding: spacing.section,
              gap: spacing.lg,
            }}
          >
            <View>
              <Text
                style={[
                  typography.bodyStrong,
                  { color: colors.text, marginBottom: 12 },
                ]}
              >
                Sortowanie
              </Text>
              <View style={styles.chips}>
                {SORTS.map((sort) =>
                  chip(sort.label, draft.sort === sort.id, () =>
                    setDraft((old) => ({ ...old, sort: sort.id })),
                  ),
                )}
              </View>
            </View>
            <View>
              <Text
                style={[
                  typography.bodyStrong,
                  { color: colors.text, marginBottom: 12 },
                ]}
              >
                Kategoria
              </Text>
              <View style={styles.chips}>
                {CATEGORY_TABS.map((category) =>
                  chip(category.label, draft.category === category.id, () =>
                    setDraft((old) => ({ ...old, category: category.id })),
                  ),
                )}
              </View>
            </View>
            <View>
              <FormField
                label="Maksymalny budżet (zł)"
                keyboardType="decimal-pad"
                placeholder="Np. 1500"
                value={budget}
                onChangeText={setBudget}
                error={errors.budget}
              />
              <FormField
                label="Minimalny potencjalny zysk (zł)"
                keyboardType="decimal-pad"
                placeholder="Np. 400"
                value={profit}
                onChangeText={setProfit}
                error={errors.profit}
              />
              <FormField
                label="Minimalny ROI (%)"
                keyboardType="decimal-pad"
                placeholder="Np. 20"
                value={roi}
                onChangeText={setRoi}
                error={errors.roi}
              />
            </View>
            <View>
              <Text
                style={[
                  typography.bodyStrong,
                  { color: colors.text, marginBottom: 12 },
                ]}
              >
                Platformy
              </Text>
              <View style={styles.chips}>
                {PLATFORMS.map((platform) =>
                  chip(
                    platformName(platform),
                    draft.platforms.includes(platform),
                    () =>
                      setDraft((old) => ({
                        ...old,
                        platforms: old.platforms.includes(platform)
                          ? old.platforms.filter((value) => value !== platform)
                          : [...old.platforms, platform],
                      })),
                  ),
                )}
              </View>
            </View>
            {onSaveProfile ? (
              <FormField
                label="Nazwa profilu wyszukiwania"
                placeholder="Np. Elektronika do 1500 zł"
                value={profileName}
                onChangeText={setProfileName}
                maxLength={60}
              />
            ) : null}
            {onSaveProfile && profileName.trim() ? (
              <PrimaryButton
                label="Zapisz profil"
                variant="secondary"
                icon="bookmark-outline"
                onPress={() => {
                  const next = validatedDraft();
                  if (next) {
                    onSaveProfile(profileName.trim(), next);
                    setProfileName("");
                  }
                }}
              />
            ) : null}
          </ScrollView>
          <View
            style={{
              paddingHorizontal: spacing.section,
              paddingTop: spacing.md,
              borderTopWidth: 1,
              borderTopColor: colors.border,
              gap: spacing.sm,
            }}
          >
            <PrimaryButton
              label="Pokaż okazje"
              icon="options-outline"
              onPress={() => {
                const next = validatedDraft();
                if (next) onApply(next);
              }}
            />
            <PrimaryButton
              label="Wyczyść filtry"
              variant="ghost"
              onPress={() => resetDraft(defaultFilters)}
            />
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: "flex-end", alignItems: "center" },
  sheet: {
    width: "100%",
    maxWidth: 640,
    flexShrink: 1,
    borderWidth: 1,
    overflow: "hidden",
  },
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: 12,
    paddingVertical: 12,
    justifyContent: "center",
  },
});
