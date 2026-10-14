import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/theme/ThemeProvider';

export function MetricCard({ label, value, help, icon, tone = 'default', loading }: {
  label: string; value: string | null; help: string; icon: keyof typeof Ionicons.glyphMap;
  tone?: 'default' | 'success' | 'warning' | 'loss'; loading?: boolean;
}) {
  const { colors, typography } = useTheme();
  const color = tone === 'success' ? colors.success : tone === 'warning' ? colors.risk : tone === 'loss' ? colors.loss : colors.text;
  return <View testID={`metric-${label}`} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
    <View style={styles.label}>
      <Text style={[typography.caption, { color: colors.textMuted, flex: 1 }]}>{label}</Text>
      <Ionicons name={icon} size={18} color={colors.accent} />
    </View>
    {loading ? <ActivityIndicator color={colors.accent} style={{ alignSelf: 'flex-start', height: 36 }} /> :
      <Text adjustsFontSizeToFit minimumFontScale={0.6} numberOfLines={1} style={[typography.title, { color: value === null ? colors.textMuted : color, fontSize: value === null ? 18 : 26 }]}>{value ?? 'Brak danych'}</Text>}
    <Text style={[typography.caption, { color: colors.textMuted }]}>{help}</Text>
  </View>;
}

const styles = StyleSheet.create({
  card: { flex: 1, minWidth: 0, borderWidth: 1, borderRadius: 16, padding: 16, gap: 12 },
  label: { flexDirection: 'row', alignItems: 'center', gap: 8 },
});
