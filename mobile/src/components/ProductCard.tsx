import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import type { OpportunityCard } from '@/features/opportunity/types';
import { useTheme } from '@/theme/ThemeProvider';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { formatRelativeSync } from '@/utils/datetime';
import { formatRoiBps } from '@/utils/money';
import { DecisionBadge } from './DecisionBadge';
import { ListingImage } from './ListingImage';
import { MoneyValue } from './MoneyValue';

type Props = {
  item: OpportunityCard;
  onPress: () => void;
  onWatch?: () => void;
  watched?: boolean;
  watchPending?: boolean;
};

export function ProductCard({ item, onPress, onWatch, watched, watchPending }: Props) {
  const { colors, radii, typography } = useTheme();
  const { isMobile } = useResponsiveLayout();
  const profit = item.hasValuation ? item.operatingProfitMinor : null;
  const roi = item.hasValuation ? item.roiBps : null;
  const profitColor = profit === null ? colors.textMuted : profit < 0 ? colors.loss : profit > 0 ? colors.success : colors.text;

  return (
    <View testID={`product-card-${item.id}`} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radii.lg }]}>
      <Pressable accessibilityRole="button" accessibilityLabel={`Szczegóły: ${item.title}`} onPress={onPress}>
        <ListingImage item={item} style={[styles.hero, isMobile && { height: 88 }]} />
        <View style={[styles.platform, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[typography.caption, { color: colors.text, fontWeight: '600' }]}>{item.platform}</Text>
        </View>
      </Pressable>
      <View style={[styles.body, isMobile && { gap: 10 }]}>
        <Pressable accessibilityRole="button" onPress={onPress}>
          <Text style={[typography.bodyStrong, !isMobile && styles.title, { color: colors.text }]} numberOfLines={2}>{item.title}</Text>
        </Pressable>
        <View style={styles.location}>
          <Ionicons name="location-outline" size={13} color={colors.textMuted} />
          <Text style={[typography.caption, { color: colors.textMuted, flex: 1 }]} numberOfLines={1}>{item.location || 'Brak lokalizacji'}{item.shipping && item.location?.toLowerCase() !== 'wysyłka' ? ' · Wysyłka' : ''}</Text>
        </View>
        {item.variant ? <Text style={[typography.caption, { color: colors.textMuted }]} numberOfLines={1}>{item.variant}</Text> : null}
        <View style={styles.prices}>
          <View style={styles.metric}><MoneyValue label="Cena zakupu" amountMinor={item.purchaseMinor} /></View>
          <View style={styles.metric}><MoneyValue label="Szacowana sprzedaż" amountMinor={item.hasValuation ? item.resaleRange?.highMinor : null} emptyLabel="Brak wyceny" /></View>
        </View>
        <View style={[styles.profit, { backgroundColor: profit === null ? colors.sidebar : profit < 0 ? colors.lossBg : colors.successBg }]}>
          <MoneyValue label="Prognozowany zysk" amountMinor={profit} emptyLabel="Brak wyceny" tone="profit" />
          <View style={{ alignItems: 'flex-end', gap: 3 }}>
            <Text style={[typography.caption, { color: colors.textMuted }]}>ROI</Text>
            <Text style={[typography.moneySmall, { color: profitColor }]}>{formatRoiBps(roi)}</Text>
          </View>
        </View>
        <View style={styles.recommendation}>
          <Text style={[typography.caption, { color: colors.textMuted }]}>Rekomendacja AI</Text>
          <DecisionBadge decision={item.decision} />
        </View>
        <Text style={[typography.caption, { color: item.topRisk ? colors.risk : colors.textMuted }]} numberOfLines={2}>
          {item.topRisk ? `Ryzyko: ${item.topRisk}` : `Weryfikacja: ${formatRelativeSync(item.verifiedAt)}`}
        </Text>
        <View style={[styles.actions, { borderTopColor: colors.border }]}>
          <Pressable accessibilityRole="button" accessibilityLabel={`Otwórz szczegóły: ${item.title}`} onPress={onPress}
            style={({ pressed }) => [styles.button, { backgroundColor: colors.accent, opacity: pressed ? 0.8 : 1 }]}>
            <Text style={[typography.caption, { color: colors.background, fontWeight: '700' }]}>Szczegóły</Text>
            <Ionicons name="arrow-forward-outline" size={15} color={colors.background} />
          </Pressable>
          {onWatch ? <Pressable accessibilityRole="button" accessibilityLabel={watched ? `Usuń z obserwowanych: ${item.title}` : `Obserwuj: ${item.title}`}
            disabled={watchPending} onPress={onWatch} style={[styles.button, { borderWidth: 1, borderColor: colors.border, opacity: watchPending ? 0.5 : 1 }]}>
            <Ionicons name={watched ? 'bookmark' : 'bookmark-outline'} size={16} color={colors.accent} />
            <Text style={[typography.caption, { color: watched ? colors.accent : colors.text, fontWeight: '600' }]}>{watchPending ? 'Zapisywanie…' : watched ? 'Zapisano' : 'Obserwuj'}</Text>
          </Pressable> : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { width: '100%', borderWidth: 1, overflow: 'hidden', minWidth: 0, flex: 1 },
  hero: { height: 124, width: '100%' },
  platform: { position: 'absolute', left: 14, top: 12, borderWidth: 1, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 },
  body: { padding: 16, gap: 12, flex: 1 },
  title: { minHeight: 42 },
  location: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  prices: { flexDirection: 'row', gap: 12 },
  metric: { flex: 1, minWidth: 0 },
  profit: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: 12, borderRadius: 10 },
  recommendation: { gap: 5 },
  actions: { borderTopWidth: 1, paddingTop: 12, flexDirection: 'row', gap: 8, marginTop: 'auto' },
  button: { flex: 1, minHeight: 44, borderRadius: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingHorizontal: 6 },
});
