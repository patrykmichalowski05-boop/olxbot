import React from 'react';
import { Tabs } from 'expo-router';
import { PremiumTabBar } from '@/components/PremiumTabBar';
import { AppScreen } from '@/components/AppScreen';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { useAuth } from '@/features/auth/AuthContext';
import { useTheme } from '@/theme/ThemeProvider';
import { AccountAccessBoundary } from '@/features/portal/AccountAccessBoundary';

export default function TabsLayout() {
  const { colors } = useTheme();
  const { ready, signedIn } = useAuth();

  return (
    <Tabs
      tabBar={(props) => <PremiumTabBar {...props} />}
      // Keep the navigator mounted so return paths retain the active screen.
      // Only the scene waits for the existing session provider to be ready.
      screenLayout={({ children }) =>
        ready && signedIn ? (
          <AccountAccessBoundary>{children}</AccountAccessBoundary>
        ) : (
          <AppScreen bottomInset={false}>
            <LoadingSkeleton rows={2} />
          </AppScreen>
        )
      }
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: colors.background },
        tabBarHideOnKeyboard: true,
      }}
    >
      <Tabs.Screen name="radar/index" options={{ title: 'Radar', href: '/radar' }} />
      <Tabs.Screen
        name="watched/index"
        options={{ title: 'Zapisane', href: '/watched' }}
      />
      <Tabs.Screen
        name="analyze/index"
        options={{ title: 'Analiza', href: '/analyze' }}
      />
      <Tabs.Screen name="flips/index" options={{ title: 'Flipy', href: '/flips' }} />
      <Tabs.Screen
        name="settings/index"
        options={{ title: 'Konto', href: '/settings' }}
      />
    </Tabs>
  );
}
