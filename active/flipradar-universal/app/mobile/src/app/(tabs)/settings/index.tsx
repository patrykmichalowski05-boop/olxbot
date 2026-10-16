import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { AppScreen } from '@/components/AppScreen';
import { Badge } from '@/components/Badge';
import { DemoBanner } from '@/components/DemoBanner';
import { Header } from '@/components/Header';
import type { IconName } from '@/components/IconButton';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useAuth } from '@/features/auth/AuthContext';
import { useTheme, type ThemePreference } from '@/theme/ThemeProvider';
import { layout } from '@/theme/tokens';

export default function SettingsScreen() {
  const router = useRouter();
  const { logout, mode } = useAuth();
  const { colors, spacing, typography, radii, preference, setPreference } = useTheme();
  const options: { id: ThemePreference; label: string; icon: IconName }[] = [
    { id: 'dark', label: 'Ciemny', icon: 'moon-outline' },
    { id: 'light', label: 'Jasny', icon: 'sunny-outline' },
    { id: 'system', label: 'Systemowy', icon: 'phone-portrait-outline' },
  ];
  return (
    <AppScreen scroll bottomInset={false}>
      <View
        style={{
          width: '100%',
          maxWidth: layout.formMaxWidth,
          alignSelf: 'center',
          gap: spacing.lg,
        }}
      >
        <View>
          <Header title="Konto i ustawienia" showNotifications={false} />
          <DemoBanner />
        </View>
        <View
          style={[
            styles.panel,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              borderRadius: radii.xxl,
              padding: spacing.section,
            },
          ]}
        >
          <View style={{ flexDirection: 'row', gap: spacing.lg, alignItems: 'center' }}>
            <View
              style={{
                width: 56,
                height: 56,
                borderRadius: radii.lg,
                backgroundColor: colors.accentBg,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Ionicons name="person-outline" size={26} color={colors.accent} />
            </View>
            <View style={{ flex: 1, gap: spacing.sm }}>
              <Text style={[typography.headline, { color: colors.text }]}>
                {mode === 'demo' ? 'Konto demonstracyjne' : 'Twoje konto FlipRadar'}
              </Text>
              <Badge
                label={mode === 'demo' ? 'Dane przykładowe' : 'Konto użytkownika'}
                tone="accent"
              />
            </View>
          </View>
        </View>
        <View
          style={[
            styles.panel,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              borderRadius: radii.xxl,
              padding: spacing.section,
              gap: spacing.lg,
            },
          ]}
        >
          <View>
            <Text style={[typography.headline, { color: colors.text }]}>
              Wygląd aplikacji
            </Text>
            <Text
              style={[
                typography.caption,
                { color: colors.textMuted, marginTop: spacing.sm },
              ]}
            >
              Wybierz motyw, w którym najlepiej Ci się pracuje.
            </Text>
          </View>
          {options.map((option) => {
            const active = preference === option.id;
            return (
              <Pressable
                key={option.id}
                accessibilityRole="radio"
                accessibilityLabel={option.label}
                accessibilityState={{ checked: active }}
                aria-checked={active}
                onPress={() => setPreference(option.id)}
                style={({ pressed }) => ({
                  minHeight: 56,
                  borderWidth: 1,
                  borderColor: active ? colors.accentMuted : colors.border,
                  borderRadius: radii.lg,
                  padding: spacing.lg,
                  backgroundColor: active ? colors.accentBg : colors.background,
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: spacing.md,
                  opacity: pressed ? 0.7 : 1,
                })}
              >
                <Ionicons
                  name={option.icon}
                  size={20}
                  color={active ? colors.accent : colors.textMuted}
                />
                <Text
                  style={[
                    typography.bodyStrong,
                    { flex: 1, color: active ? colors.accent : colors.text },
                  ]}
                >
                  {option.label}
                </Text>
                <Ionicons
                  name={active ? 'checkmark-circle' : 'ellipse-outline'}
                  size={20}
                  color={active ? colors.accent : colors.textSubtle}
                />
              </Pressable>
            );
          })}
        </View>
        <PrimaryButton
          label="Moje wyszukiwania i alerty"
          icon="search-outline"
          onPress={() => router.push('/searches')}
        />
        <PrimaryButton
          label="Wyloguj się"
          variant="secondary"
          icon="log-out-outline"
          onPress={() => {
            void logout();
          }}
        />
        <Text
          style={[typography.caption, { color: colors.textSubtle, textAlign: 'center' }]}
        >
          FlipRadar · Twoje centrum okazji
        </Text>
      </View>
    </AppScreen>
  );
}
const styles = StyleSheet.create({ panel: { borderWidth: 1 } });
