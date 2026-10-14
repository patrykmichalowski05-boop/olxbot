import React from 'react';
import { View, useWindowDimensions } from 'react-native';
import { Stack, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from '@/features/auth/AuthContext';
import { ThemeProvider, useTheme } from '@/theme/ThemeProvider';
import { DesktopSidebar } from '@/components/DesktopSidebar';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function RootNavigator() {
  const { colors, isDark } = useTheme();
  const { width } = useWindowDimensions();
  const segments = useSegments();
  const showSidebar = width >= 1000 && segments[0] !== '(auth)';

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <View style={{
        flex: 1,
        flexDirection: 'row',
        backgroundColor: colors.background,
      }}>
        {showSidebar ? <DesktopSidebar /> : null}
        <View style={{ flex: 1, minWidth: 0 }}>
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="(auth)/login" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="offer/[id]" options={{ presentation: 'card' }} />
        <Stack.Screen name="notifications/index" />
        <Stack.Screen name="flips/[dealId]" />
        <Stack.Screen name="purchase/[listingId]" />
        <Stack.Screen name="analytics/index" />
      </Stack>
        </View>
      </View>
    </>
  );
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <RootNavigator />
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
