import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

import { useTheme } from '@/theme/ThemeProvider';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';

export default function TabsLayout() {
  const { colors } = useTheme();
  const { isMobile } = useResponsiveLayout();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: colors.background },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          display: isMobile ? 'flex' : 'none',
        },
        tabBarLabelStyle: { fontSize: 10 },
      }}
    >
      <Tabs.Screen name="dashboard/index" options={{ title: 'Dashboard', tabBarLabel: 'Start', href: '/dashboard', tabBarIcon: ({ color, size }) => <Ionicons name="grid-outline" size={size} color={color} /> }} />
      <Tabs.Screen
        name="radar/index"
        options={{
          title: 'Radar',
          href: '/radar',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="radio-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="watched/index"
        options={{
          title: 'Obserwowane',
          tabBarLabel: 'Zapisane',
          href: '/watched',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="bookmark-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="analyze/index"
        options={{
          title: 'Analizuj',
          href: '/analyze',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="scan-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="flips/index"
        options={{
          title: 'Moje flipy',
          tabBarLabel: 'Flipy',
          href: '/flips',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="briefcase-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings/index"
        options={{
          title: 'Ustawienia',
          tabBarLabel: 'Konto',
          href: '/settings',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="settings-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
