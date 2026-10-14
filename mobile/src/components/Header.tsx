import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

import { useTheme } from '@/theme/ThemeProvider';
import { touchTarget } from '@/theme/tokens';

type Props = {
  title: string;
  subtitle?: string;
  showBack?: boolean;
  onBack?: () => void;
  rightSlot?: React.ReactNode;
  showNotifications?: boolean;
};

export function Header({
  title,
  subtitle,
  showBack,
  onBack,
  rightSlot,
  showNotifications = true,
}: Props) {
  const { colors, spacing, typography } = useTheme();
  const router = useRouter();

  return (
    <View style={[styles.row, { marginBottom: spacing.md, gap: spacing.sm }]}>
      {showBack ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Wróć"
          onPress={onBack ?? (() => router.back())}
          style={[styles.iconBtn, { minHeight: touchTarget, minWidth: touchTarget }]}
        >
          <Ionicons name="chevron-back" size={24} color={colors.text} />
        </Pressable>
      ) : (
        <View style={{ width: touchTarget }} />
      )}

      <View style={styles.titleWrap}>
        <Text style={[typography.headline, { color: colors.text }]} numberOfLines={1}>
          {title}
        </Text>
        {subtitle ? (
          <Text style={[typography.caption, { color: colors.textMuted }]} numberOfLines={1}>
            {subtitle}
          </Text>
        ) : null}
      </View>

      <View style={styles.actions}>
        {rightSlot}
        {showNotifications ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Powiadomienia"
            onPress={() => router.push('/notifications')}
            style={[styles.iconBtn, { minHeight: touchTarget, minWidth: touchTarget }]}
          >
            <Ionicons name="notifications-outline" size={22} color={colors.text} />
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  titleWrap: { flex: 1 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  iconBtn: { alignItems: 'center', justifyContent: 'center' },
});
