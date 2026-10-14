import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { NotificationView } from '@/api/mappers/notification';
import { useTheme } from '@/theme/ThemeProvider';
import { formatUserDateTime } from '@/utils/datetime';

export function NotificationCard({ item, compact }: { item: NotificationView; compact?: boolean }) {
  const { colors, typography } = useTheme();
  const risk = item.category === 'Ryzyko';
  const icon = risk ? 'warning-outline' : item.category === 'Cena' ? 'trending-down-outline' : item.category === 'Flip' ? 'briefcase-outline' : 'notifications-outline';
  return <View style={[styles.row, { padding: compact ? 0 : 16, backgroundColor: compact ? 'transparent' : colors.surface, borderColor: colors.border, borderWidth: compact ? 0 : 1 }]}>
    <View style={[styles.icon, { backgroundColor: risk ? colors.riskBg : colors.accentMuted }]}><Ionicons name={icon} size={20} color={risk ? colors.risk : colors.accent} /></View>
    <View style={{ flex: 1, minWidth: 0, gap: 5 }}>
      <View style={styles.heading}>
        <Text style={[typography.caption, { color: risk ? colors.risk : colors.accent }]}>{item.category}</Text>
        <Text style={[typography.caption, { color: colors.textMuted }]}>{formatUserDateTime(item.at)}</Text>
      </View>
      <Text style={[typography.bodyStrong, { color: colors.text }]}>{item.title}</Text>
      <Text style={[typography.caption, { color: colors.textMuted }]} numberOfLines={compact ? 3 : undefined}>{item.reason}</Text>
    </View>
  </View>;
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12, borderRadius: 12, minWidth: 0 },
  icon: { width: 40, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  heading: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 4 },
});
