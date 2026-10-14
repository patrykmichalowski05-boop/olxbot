import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { OpportunityCard } from '@/features/opportunity/types';
import { useTheme } from '@/theme/ThemeProvider';
import { formatMoneyMinor } from '@/utils/money';
import { ListingImage } from './ListingImage';
import { DecisionBadge } from './DecisionBadge';

export function OpportunityRow({ item, onPress }: { item: OpportunityCard; onPress: () => void }) {
  const { colors, typography } = useTheme();
  const profit = item.hasValuation ? item.operatingProfitMinor : null;
  return <Pressable accessibilityRole="button" accessibilityLabel={`Oferta: ${item.title}`} onPress={onPress} style={[styles.row, { borderColor: colors.border }]}>
    <ListingImage item={item} compact style={styles.thumb} />
    <View style={{ flex: 1, minWidth: 0, gap: 6 }}>
      <Text style={[typography.bodyStrong, { color: colors.text }]} numberOfLines={2}>{item.title}</Text>
      <Text style={[typography.caption, { color: colors.textMuted }]}>{item.platform}{item.location ? ` · ${item.location}` : ''}</Text>
      <View style={styles.details}>
        <DecisionBadge decision={item.decision} />
        <Text style={[typography.caption, { color: profit === null ? colors.textMuted : profit < 0 ? colors.loss : colors.success, fontWeight: '600' }]}>{profit === null ? 'Brak wyceny' : `Zysk (prognoza): ${formatMoneyMinor(profit)}`}</Text>
      </View>
    </View>
  </Pressable>;
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12, alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1 },
  thumb: { width: 48, height: 48, borderRadius: 10 },
  details: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8 },
});
