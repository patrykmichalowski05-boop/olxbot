import React, { useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { RadarFilters } from '@/features/radar/filterStore';
import { defaultFilters } from '@/features/radar/filterStore';
import { useTheme } from '@/theme/ThemeProvider';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { parseMoneyInput } from '@/utils/money';
import { FormField } from './FormField';
import { PrimaryButton } from './PrimaryButton';

type Props = {
  visible: boolean;
  initial: RadarFilters;
  onClose: () => void;
  onApply: (filters: RadarFilters) => void;
  onSaveProfile?: (name: string, filters: RadarFilters) => void;
};

const PLATFORMS = ['OLX', 'FACEBOOK', 'VINTED', 'OTOMOTO', 'ALLEGRO', 'EBAY'];

export function FilterSheet(props: Props) {
  return props.visible ? <FilterSheetContent {...props} /> : null;
}

function FilterSheetContent({
  visible,
  initial,
  onClose,
  onApply,
  onSaveProfile,
}: Props) {
  const { colors, spacing, typography, radii } = useTheme();
  const [draft, setDraft] = useState(initial);
  const [profileName, setProfileName] = useState('');
  const insets = useSafeAreaInsets();

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={[styles.root, { backgroundColor: colors.overlay, paddingHorizontal: spacing.lg, paddingTop: insets.top + spacing.lg, paddingBottom: insets.bottom + spacing.lg }]}>
        <View style={[styles.sheet, { backgroundColor: colors.surface, padding: spacing.lg, borderRadius: radii.lg, borderColor: colors.border }]}>
        <Text style={[typography.title, { color: colors.text }]}>Filtry</Text>
        <ScrollView contentContainerStyle={{ gap: spacing.md, paddingVertical: spacing.md }}>
          <FormField
            label="Maks. budżet (zł)"
            keyboardType="decimal-pad"
            value={
              draft.maxBudgetMinor !== null
                ? String(draft.maxBudgetMinor / 100).replace('.', ',')
                : ''
            }
            onChangeText={(text) =>
              setDraft((d) => ({
                ...d,
                maxBudgetMinor: parseMoneyInput(text),
              }))
            }
          />
          <FormField
            label="Min. potencjalny zysk (zł)"
            keyboardType="decimal-pad"
            value={
              draft.minProfitMinor !== null
                ? String(draft.minProfitMinor / 100).replace('.', ',')
                : ''
            }
            onChangeText={(text) =>
              setDraft((d) => ({
                ...d,
                minProfitMinor: parseMoneyInput(text),
              }))
            }
          />
          <FormField
            label="Min. ROI (%)"
            keyboardType="decimal-pad"
            value={
              draft.minRoiBps !== null ? String(draft.minRoiBps / 100).replace('.', ',') : ''
            }
            onChangeText={(text) => {
              const normalized = text.replace(',', '.');
              const value = normalized ? Number(normalized) : null;
              setDraft((d) => ({
                ...d,
                minRoiBps:
                  value !== null && Number.isFinite(value)
                    ? Math.round(value * 100)
                    : null,
              }));
            }}
          />

          <Text style={[typography.bodyStrong, { color: colors.text }]}>Platformy</Text>
          <View style={styles.chips}>
            {PLATFORMS.map((platform) => {
              const active = draft.platforms.includes(platform);
              return (
                <Pressable
                  key={platform}
                  onPress={() =>
                    setDraft((d) => ({
                      ...d,
                      platforms: active
                        ? d.platforms.filter((p) => p !== platform)
                        : [...d.platforms, platform],
                    }))
                  }
                  style={[
                    styles.chip,
                    {
                      borderColor: colors.border,
                      backgroundColor: active ? colors.accent : colors.surface,
                      borderRadius: radii.pill,
                    },
                  ]}
                >
                  <Text
                    style={[
                      typography.caption,
                      { color: active ? colors.background : colors.text },
                    ]}
                  >
                    {platform}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {onSaveProfile ? (
            <FormField
              label="Zapisz jako profil wyszukiwania"
              value={profileName}
              onChangeText={setProfileName}
              placeholder="Np. Auta do 50 tys."
            />
          ) : null}
        </ScrollView>

        <View style={{ gap: spacing.sm }}>
          {onSaveProfile && profileName.trim() ? (
            <PrimaryButton
              label="Zapisz profil"
              variant="secondary"
              onPress={() => {
                onSaveProfile(profileName.trim(), draft);
                setProfileName('');
              }}
            />
          ) : null}
          <PrimaryButton label="Zastosuj filtry" onPress={() => onApply(draft)} />
          <PrimaryButton
            label="Resetuj"
            variant="ghost"
            onPress={() => setDraft(defaultFilters)}
          />
          <PrimaryButton label="Zamknij" variant="ghost" onPress={onClose} />
        </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  sheet: { width: '100%', maxWidth: 560, maxHeight: '100%', borderWidth: 1, flexShrink: 1 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
});
