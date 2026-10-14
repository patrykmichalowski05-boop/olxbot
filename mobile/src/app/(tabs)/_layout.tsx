import React from 'react';
import { useWindowDimensions } from 'react-native';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

import { useTheme } from '@/theme/ThemeProvider';

export default function TabsLayout() {
  const { colors, isDark } = useTheme();
  const { width } = useWindowDimensions();
  const wide = width >= 900;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          ...(wide
            ? {
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: 88,
                borderTopWidth: 0,
                borderRightWidth: 1,
                borderRightColor: colors.border,
                flexDirection: 'column',
              }
            : {}),
        },
        tabBarLabelStyle: { fontSize: 11 },
      }}
    >
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
          href: '/settings',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="settings-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
