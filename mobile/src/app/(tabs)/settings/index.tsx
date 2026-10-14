import React from 'react';
import { Text, View } from 'react-native';

import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { Header } from '@/components/Header';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useAuth } from '@/features/auth/AuthContext';
import { useTheme } from '@/theme/ThemeProvider';
import type { ThemePreference } from '@/theme/ThemeProvider';
import { apiBaseUrl, workspaceId } from '@/utils/config';

export default function SettingsScreen() {
  const { logout, mode, userId } = useAuth();
  const { colors, spacing, typography, preference, setPreference } = useTheme();

  const options: { id: ThemePreference; label: string }[] = [
    { id: 'system', label: 'Zgodnie z systemem' },
    { id: 'dark', label: 'Ciemny' },
    { id: 'light', label: 'Jasny' },
  ];

  return (
    <AppScreen scroll>
      <Header title="Ustawienia" showNotifications={false} />
      <DemoBanner />

      <View style={{ gap: spacing.md, marginBottom: spacing.xl }}>
        <Text style={[typography.bodyStrong, { color: colors.text }]}>Konto</Text>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          Użytkownik: {userId ?? '—'}
        </Text>
        <Text style={[typography.body, { color: colors.textMuted }]}>
          Tryb: {mode === 'demo' ? 'DEMO' : 'LIVE'}
        </Text>
        <Text style={[typography.caption, { color: colors.textMuted }]}>
          API: {apiBaseUrl() || 'nie skonfigurowane'}
        </Text>
        <Text style={[typography.caption, { color: colors.textMuted }]}>
          Workspace: {workspaceId() ?? 'brak (wymagane dla API v2 flipów)'}
        </Text>
      </View>

      <Text style={[typography.bodyStrong, { color: colors.text, marginBottom: spacing.sm }]}>
        Motyw
      </Text>
      {options.map((option) => (
        <PrimaryButton
          key={option.id}
          label={`${option.label}${preference === option.id ? ' ✓' : ''}`}
          variant={preference === option.id ? 'primary' : 'secondary'}
          onPress={() => setPreference(option.id)}
          style={{ marginBottom: spacing.sm }}
        />
      ))}

      <View style={{ marginTop: spacing.xl }}>
        <PrimaryButton label="Wyloguj" variant="secondary" onPress={() => void logout()} />
      </View>

      <Text style={[typography.caption, { color: colors.textMuted, marginTop: spacing.lg }]}>
        Powiadomienia push i menu udostępniania wymagają osobnej konfiguracji natywnej — patrz
        GUI_IMPLEMENTATION.md.
      </Text>
    </AppScreen>
  );
}
