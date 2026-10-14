import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { usePathname, useRouter, type Href } from 'expo-router';

import { useTheme } from '@/theme/ThemeProvider';

type MenuItem = {
  path: string;
  title: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
};

const menu: MenuItem[] = [
  { path: '/radar', title: 'Radar okazji', icon: 'radio-outline' },
  { path: '/watched', title: 'Obserwowane', icon: 'bookmark-outline' },
  { path: '/analyze', title: 'Analiza AI', icon: 'scan-outline' },
  { path: '/flips', title: 'Moje flipy', icon: 'briefcase-outline' },
  { path: '/analytics', title: 'Analityka', icon: 'stats-chart-outline' },
  { path: '/notifications', title: 'Powiadomienia', icon: 'notifications-outline' },
  { path: '/settings', title: 'Ustawienia', icon: 'settings-outline' },
];

export function DesktopSidebar() {
  const { colors, spacing, typography, radii } = useTheme();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <View style={{
      width: 248,
      flexShrink: 0,
      backgroundColor: colors.surface,
      borderRightWidth: 1,
      borderRightColor: colors.border,
      paddingHorizontal: spacing.lg,
      paddingTop: spacing.xxl,
      paddingBottom: spacing.xl,
      justifyContent: 'space-between',
    }}>
      <View>
        <View style={{
          flexDirection: 'row',
          gap: 12,
          alignItems: 'center',
          marginBottom: 42,
        }}>
          <View style={{
            width: 44,
            height: 44,
            borderRadius: 13,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: colors.accent,
          }}>
            <Ionicons
              name="flash"
              size={22}
              color={colors.background}
            />
          </View>

          <View>
            <Text style={{
              color: colors.text,
              fontSize: 21,
              fontWeight: '800',
            }}>
              FlipRadar
            </Text>

            <Text style={[
              typography.caption,
              {
                color: colors.textMuted,
                letterSpacing: 1.3,
              },
            ]}>
              FLIP HUNTER
            </Text>
          </View>
        </View>

        <Text style={[
          typography.caption,
          {
            color: colors.textMuted,
            fontWeight: '700',
            letterSpacing: 1.5,
            marginBottom: spacing.md,
            paddingHorizontal: spacing.md,
          },
        ]}>
          NAWIGACJA
        </Text>

        {menu.map((item) => {
          const active =
            pathname === item.path ||
            pathname.startsWith(`${item.path}/`);

          return (
            <Pressable
              key={item.path}
              accessibilityRole="link"
              accessibilityLabel={item.title}
              onPress={() => router.push(item.path as Href)}
              style={({ pressed }) => ({
                minHeight: 48,
                flexDirection: 'row',
                alignItems: 'center',
                gap: 13,
                paddingHorizontal: spacing.md,
                marginBottom: spacing.xs,
                borderRadius: radii.md,
                backgroundColor: active || pressed
                  ? colors.surfaceElevated
                  : 'transparent',
                borderWidth: 1,
                borderColor: active
                  ? colors.accentMuted
                  : 'transparent',
              })}
            >
              <Ionicons
                name={item.icon}
                size={20}
                color={active ? colors.accent : colors.textMuted}
              />

              <Text style={[
                typography.body,
                {
                  color: active ? colors.text : colors.textMuted,
                  fontWeight: active ? '700' : '500',
                },
              ]}>
                {item.title}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <View style={{
        borderTopWidth: 1,
        borderTopColor: colors.border,
        paddingTop: spacing.lg,
        gap: 6,
      }}>
        <Text style={[
          typography.caption,
          { color: colors.accent, fontWeight: '700' },
        ]}>
          FLIPRADAR • DEVELOPMENT
        </Text>

        <Text style={[
          typography.caption,
          { color: colors.textMuted },
        ]}>
          Wersja testowa interfejsu
        </Text>
      </View>
    </View>
  );
}
