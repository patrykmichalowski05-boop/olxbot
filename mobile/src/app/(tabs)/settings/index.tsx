import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { Header } from '@/components/Header';
import { Panel } from '@/components/Panel';
import { PrimaryButton } from '@/components/PrimaryButton';
import { ResponsiveGrid } from '@/components/ResponsiveGrid';
import { useAuth } from '@/features/auth/AuthContext';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme, type ThemePreference } from '@/theme/ThemeProvider';
import { apiBaseUrl, workspaceId } from '@/utils/config';

export default function SettingsScreen() {
  const { logout, mode, userId, checkConnection } = useAuth();
  const router = useRouter();
  const { colors, typography, preference, setPreference } = useTheme();
  const { isMobile } = useResponsiveLayout();
  const [message, setMessage] = useState('');
  const [checking, setChecking] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const options: { id: ThemePreference; label: string }[] = [{ id: 'dark', label: 'Ciemny' }, { id: 'light', label: 'Jasny' }, { id: 'system', label: 'Systemowy' }];
  return <AppScreen scroll maxWidth={1280}>
    <Header title="Ustawienia" subtitle="Konto, wygląd i źródło danych" showNotifications={false} />
    <DemoBanner />
    <View style={{ gap: 24 }}>
      <ResponsiveGrid columns={isMobile ? 1 : 2}>
        <Panel title="Konto">
          <Text style={[typography.caption, { color: colors.textMuted }]}>Użytkownik</Text>
          <Text style={[typography.bodyStrong, { color: colors.text }]}>{userId ?? 'Brak danych'}</Text>
          <View style={{ alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 6, backgroundColor: mode === 'demo' ? colors.riskBg : colors.successBg, borderRadius: 8 }}>
            <Text style={[typography.caption, { color: mode === 'demo' ? colors.risk : colors.success }]}>{mode.toUpperCase()}</Text>
          </View>
          <Text style={[typography.caption, { color: colors.textMuted }]}>{mode === 'demo' ? 'Dane demonstracyjne. Operacje nie trafiają do LIVE.' : 'Dane i operacje Twojej przestrzeni transakcji.'}</Text>
          <PrimaryButton label="Wyloguj" variant="secondary" loading={loggingOut} onPress={async () => {
            setLoggingOut(true);
            try { await logout(); } catch (error) { setMessage(apiErrorMessage(error)); } finally { setLoggingOut(false); }
          }} />
        </Panel>
        <Panel title="Wygląd" subtitle="Domyślnie ciemny. Wybrany motyw zostaje zapamiętany.">
          {options.map(option => <PrimaryButton key={option.id} label={option.label + (preference === option.id ? ' · wybrany' : '')}
            variant={preference === option.id ? 'primary' : 'secondary'} onPress={() => setPreference(option.id)} />)}
        </Panel>
        <Panel title="Przestrzeń robocza" subtitle="Przegląd danych i zdarzeń">
          <PrimaryButton label="Dashboard" variant="secondary" onPress={() => router.push('/dashboard')} />
          <PrimaryButton label="Analityka" variant="secondary" onPress={() => router.push('/analytics')} />
          <PrimaryButton label="Powiadomienia" variant="secondary" onPress={() => router.push('/notifications')} />
          <Text style={[typography.caption, { color: colors.textMuted }]}>Powiadomienia push są jeszcze niedostępne. Zdarzenia możesz sprawdzać w skrzynce powiadomień.</Text>
        </Panel>
        <Panel title="Połączenie z danymi">
          <Text style={[typography.caption, { color: colors.textMuted }]}>Adres API</Text>
          <Text style={[typography.body, { color: colors.text }]}>{apiBaseUrl() || 'Nie skonfigurowano'}</Text>
          <Text style={[typography.caption, { color: colors.textMuted }]}>Workspace</Text>
          <Text style={[typography.body, { color: colors.text }]}>{workspaceId() ?? 'Nie skonfigurowano'}</Text>
          <PrimaryButton label="Sprawdź połączenie" variant="secondary" loading={checking} onPress={async () => {
            setChecking(true); setMessage('');
            try { setMessage(await checkConnection()); } catch (error) { setMessage(apiErrorMessage(error)); } finally { setChecking(false); }
          }} />
          {message ? <Text accessibilityLiveRegion="polite" style={[typography.caption, { color: colors.textMuted }]}>{message}</Text> : null}
        </Panel>
      </ResponsiveGrid>
    </View>
  </AppScreen>;
}
