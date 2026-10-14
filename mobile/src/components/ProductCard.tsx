import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import type { OpportunityCard } from '@/features/opportunity/types';
import { useTheme } from '@/theme/ThemeProvider';
import { formatRelativeSync } from '@/utils/datetime';
import { DecisionBadge } from './DecisionBadge';
import { MoneyValue } from './MoneyValue';

type Props = {
  item: OpportunityCard;
  onPress: () => void;
  onWatch?: () => void;
  watched?: boolean;
};

export function ProductCard({ item, onPress, onWatch, watched }: Props) {
  const { colors, radii, spacing, typography } = useTheme();

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: colors.surface,
          borderRadius: radii.md,
          borderColor: colors.border,
          opacity: pressed ? 0.92 : 1,
          padding: spacing.md,
          gap: spacing.sm,
        },
      ]}
    >
      <View style={styles.topRow}>
        <View style={[styles.thumb, { backgroundColor: colors.surfaceElevated, borderRadius: radii.sm }]}>
          {item.imageUrl ? (
            <Image source={{ uri: item.imageUrl }} style={styles.thumbImg} />
          ) : (
            <Ionicons name="cube-outline" size={28} color={colors.textMuted} />
          )}
        </View>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={[typography.caption, { color: colors.textMuted }]}>
            {item.platform}
            {item.location ? ` · ${item.location}` : ''}
          </Text>
          <Text style={[typography.bodyStrong, { color: colors.text }]} numberOfLines={2}>
            {item.title}
          </Text>
          {item.variant ? (
            <Text style={[typography.caption, { color: colors.textMuted }]} numberOfLines={1}>
              {item.variant}
            </Text>
          ) : null}
        </View>
        {onWatch ? (
          <Pressable
            accessibilityLabel={watched ? 'Usuń z obserwowanych' : 'Dodaj do obserwowanych'}
            onPress={(e) => {
              e.stopPropagation?.();
              onWatch();
            }}
            hitSlop={8}
          >
            <Ionicons
              name={watched ? 'bookmark' : 'bookmark-outline'}
              size={22}
              color={colors.accent}
            />
          </Pressable>
        ) : null}
      </View>

      <View style={styles.metrics}>
        <MoneyValue label="Cena zakupu" amountMinor={item.purchaseMinor} emphasize />
        <MoneyValue
          label="Prognoza odsprzedaży"
          amountMinor={item.resaleRange?.highMinor ?? null}
          emptyLabel="Brak wyceny"
        />
        <MoneyValue
          label="Potencjalny wynik operacyjny"
          amountMinor={item.operatingProfitMinor}
          roiBps={item.roiBps}
          emptyLabel="—"
        />
      </View>

      <View style={styles.footer}>
        <DecisionBadge decision={item.decision} />
        <Text style={[typography.caption, { color: colors.textMuted, flex: 1 }]} numberOfLines={1}>
          {item.topRisk ? `Ryzyko: ${item.topRisk}` : `Weryfikacja: ${formatRelativeSync(item.verifiedAt)}`}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1 },
  topRow: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  thumb: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  thumbImg: { width: '100%', height: '100%' },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: 16 },
  footer: { flexDirection: 'row', gap: 8, alignItems: 'center' },
});
