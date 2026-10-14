import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import type { OpportunityCard } from '@/features/opportunity/types';
import { useTheme } from '@/theme/ThemeProvider';
import { formatMoneyMinor, formatRoiBps } from '@/utils/money';
import { DecisionBadge } from './DecisionBadge';
import { ListingImage } from './ListingImage';

export const PRODUCT_TABLE_MIN_WIDTH = 1232;
const cells = [
  { title: 'Oferta / lokalizacja', width: 0 },
  { title: 'Platforma', width: 92 },
  { title: 'Zakup', width: 118 },
  { title: 'Sprzedaż (szac.)', width: 132 },
  { title: 'Zysk (prognoza)', width: 132 },
  { title: 'ROI', width: 76 },
  { title: 'Rekomendacja AI', width: 192 },
  { title: 'Działania', width: 138 },
];

export function ProductTableHeader() {
  const { colors, typography } = useTheme();
  return <View style={[styles.row, styles.heading, { backgroundColor: colors.sidebar, borderColor: colors.border }]}>
    {cells.map(({ title, width }) => <Text key={title} style={[typography.caption, width ? { width } : styles.offer, { color: colors.textMuted, fontWeight: '600' }]}>{title}</Text>)}
  </View>;
}

export function ProductTableRow({ item, onPress, onWatch, watched, pending }: {
  item: OpportunityCard; onPress: () => void; onWatch: () => void; watched: boolean; pending: boolean;
}) {
  const { colors, typography } = useTheme();
  const profit = item.hasValuation ? item.operatingProfitMinor : null;
  const values = [item.platform, formatMoneyMinor(item.purchaseMinor), formatMoneyMinor(item.hasValuation ? item.resaleRange?.highMinor : null, 'PLN', { emptyLabel: 'Brak wyceny' }), formatMoneyMinor(profit, 'PLN', { emptyLabel: 'Brak wyceny' }), formatRoiBps(item.hasValuation ? item.roiBps : null)];

  return <View style={[styles.row, { backgroundColor: colors.surface, borderColor: colors.border }]}>
    <Pressable accessibilityRole="button" accessibilityLabel={`Szczegóły: ${item.title}`} onPress={onPress} style={[styles.offer, styles.offerLink]}>
      <ListingImage item={item} compact style={styles.thumb} />
      <View style={{ flex: 1, minWidth: 0, gap: 4 }}>
        <Text style={[typography.bodyStrong, { color: colors.text }]} numberOfLines={2}>{item.title}</Text>
        <Text style={[typography.caption, { color: colors.textMuted }]} numberOfLines={1}>{item.location || 'Brak lokalizacji'}</Text>
      </View>
    </Pressable>
    {values.map((value, index) => <Text key={index} style={[typography.caption, { width: cells[index + 1]!.width, color: index === 3 && profit !== null ? profit < 0 ? colors.loss : profit > 0 ? colors.success : colors.text : colors.text, fontWeight: index >= 1 ? '600' : '400' }]}>{value}</Text>)}
    <View style={{ width: cells[6]!.width }}><DecisionBadge decision={item.decision} /></View>
    <View style={[styles.buttons, { width: cells[7]!.width }]}>
      <Pressable accessibilityRole="button" accessibilityLabel={`Otwórz szczegóły: ${item.title}`} onPress={onPress} style={[styles.detail, { backgroundColor: colors.accentMuted }]}>
        <Text style={[typography.caption, { color: colors.accent, fontWeight: '600' }]}>Szczegóły</Text>
      </Pressable>
      <Pressable accessibilityRole="button" accessibilityLabel={watched ? `Usuń z obserwowanych: ${item.title}` : `Obserwuj: ${item.title}`} disabled={pending} onPress={onWatch} style={[styles.watch, { opacity: pending ? 0.4 : 1 }]}>
        <Ionicons name={watched ? 'bookmark' : 'bookmark-outline'} size={20} color={colors.accent} />
      </Pressable>
    </View>
  </View>;
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, minHeight: 90 },
  heading: { minHeight: 46, paddingVertical: 12 },
  offer: { flex: 1, minWidth: 220, paddingRight: 12 },
  offerLink: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  thumb: { width: 44, height: 44, borderRadius: 8 },
  buttons: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  detail: { minHeight: 44, paddingHorizontal: 10, borderRadius: 8, justifyContent: 'center' },
  watch: { width: 40, height: 44, alignItems: 'center', justifyContent: 'center' },
});
