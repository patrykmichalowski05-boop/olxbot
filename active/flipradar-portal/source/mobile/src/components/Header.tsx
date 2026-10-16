import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '@/theme/ThemeProvider';
import { IconButton } from './IconButton';

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
    <View style={[styles.row, { marginBottom: spacing.lg, gap: spacing.md }]}>
      {showBack ? (
        <IconButton
          icon="chevron-back"
          label="Wróć"
          onPress={onBack ?? (() => router.back())}
        />
      ) : null}
      <View style={styles.titleWrap}>
        {!showBack ? (
          <Text style={[typography.label, { color: colors.accent, marginBottom: 4 }]}>
            FLIPRADAR
          </Text>
        ) : null}
        <Text
          style={[typography.title, { color: colors.text }]}
          numberOfLines={1}
          adjustsFontSizeToFit
          minimumFontScale={0.8}
        >
          {title}
        </Text>
        {subtitle ? (
          <Text style={[typography.caption, { color: colors.textMuted, marginTop: 4 }]}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      <View style={styles.actions}>
        {rightSlot}
        {showNotifications ? (
          <IconButton
            icon="notifications-outline"
            label="Powiadomienia"
            onPress={() => router.push('/notifications')}
          />
        ) : null}
      </View>
    </View>
  );
}
const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  titleWrap: { flex: 1, minWidth: 0 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
});
