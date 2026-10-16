import React, { useEffect, useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { OpportunityCard } from '@/features/opportunity/types';
import {
  isHotDeal,
  opportunityInsight,
  opportunityRisk,
} from '@/features/opportunity/presentation';
import { useTheme } from '@/theme/ThemeProvider';
import { formatRelativeSync } from '@/utils/datetime';
import { formatMoneyMinor, formatRoiBps, formatSignedMoneyMinor } from '@/utils/money';
import { Badge } from './Badge';
import { DecisionBadge } from './DecisionBadge';
import { IconButton, type IconName } from './IconButton';

const categoryIcons: Record<string, IconName> = {
  CAR: 'car-sport-outline',
  ELECTRONICS: 'hardware-chip-outline',
  FASHION: 'shirt-outline',
  OTHER: 'cube-outline',
};
type Props = {
  item: OpportunityCard;
  onPress: () => void;
  onWatch?: () => void;
  watched?: boolean;
  watchLoading?: boolean;
  watchDisabled?: boolean;
};
export function ProductCard({
  item,
  onPress,
  onWatch,
  watched,
  watchLoading,
  watchDisabled,
}: Props) {
  const { colors, radii, spacing, typography } = useTheme();
  const [imageFailed, setImageFailed] = useState(false);
  useEffect(() => setImageFailed(false), [item.imageUrl]);
  const risk = opportunityRisk(item);
  const insight = opportunityInsight(item);
  const hot = isHotDeal(item);
  const profit = item.hasValuation ? item.operatingProfitMinor : null;
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.surface,
          borderColor: hot ? colors.accentMuted : colors.border,
          borderRadius: radii.xxl,
          padding: spacing.lg,
          gap: spacing.lg,
        },
      ]}
    >
      <View style={styles.top}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Szczegóły: ${item.title}`}
          onPress={onPress}
          style={({ pressed }) => [styles.summary, { opacity: pressed ? 0.7 : 1 }]}
        >
          <View
            style={[
              styles.thumb,
              { backgroundColor: colors.surfaceElevated, borderRadius: radii.lg },
            ]}
          >
            {item.imageUrl && !imageFailed ? (
              <Image
                source={{ uri: item.imageUrl }}
                style={styles.image}
                resizeMode="cover"
                onError={() => setImageFailed(true)}
              />
            ) : (
              <>
                <Ionicons
                  name={categoryIcons[item.category] ?? 'cube-outline'}
                  size={28}
                  color={colors.textSubtle}
                />
                <Text style={{ fontSize: 9, color: colors.textSubtle, marginTop: 4 }}>
                  Brak zdjęcia
                </Text>
              </>
            )}
          </View>
          <View style={{ flex: 1, gap: 6, minWidth: 0 }}>
            <Badge
              label={
                item.platform.toUpperCase() === 'MANUAL'
                  ? 'WŁASNE'
                  : item.platform.toUpperCase()
              }
              tone="accent"
            />
            <Text
              style={[typography.bodyStrong, { color: colors.text }]}
              numberOfLines={2}
            >
              {item.title}
            </Text>
            <Text
              style={[typography.caption, { color: colors.textSubtle }]}
              numberOfLines={1}
            >
              {item.location ?? item.variant ?? 'Oferta z radaru'}
            </Text>
          </View>
        </Pressable>
        {onWatch ? (
          <IconButton
            icon={watched ? 'bookmark' : 'bookmark-outline'}
            label={watched ? 'Usuń z zapisanych' : 'Zapisz ofertę'}
            active={watched}
            loading={watchLoading}
            disabled={watchDisabled}
            onPress={onWatch}
          />
        ) : null}
      </View>
      <View style={styles.badges}>
        <DecisionBadge decision={item.decision} compact />
        <Badge label={risk.label} tone={risk.tone} icon="shield-half-outline" />
        {hot ? <Badge label="Hot deal" tone="success" icon="flame-outline" /> : null}
      </View>
      <View style={styles.prices}>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={[typography.caption, { color: colors.textMuted }]}>
            Cena zakupu
          </Text>
          <Text
            style={[
              typography.moneySmall,
              { color: colors.text, fontVariant: ['tabular-nums'] },
            ]}
          >
            {formatMoneyMinor(item.purchaseMinor, 'PLN', { emptyLabel: 'Brak ceny' })}
          </Text>
        </View>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={[typography.caption, { color: colors.textMuted }]}>
            Prognoza odsprzedaży
          </Text>
          <Text
            style={[
              typography.moneySmall,
              { color: colors.text, fontVariant: ['tabular-nums'] },
            ]}
          >
            {formatMoneyMinor(
              item.hasValuation ? item.resaleRange?.highMinor : null,
              'PLN',
              { emptyLabel: 'Brak wyceny' },
            )}
          </Text>
        </View>
      </View>
      <View
        style={[
          styles.profit,
          {
            backgroundColor:
              profit === null
                ? colors.surfaceElevated
                : profit >= 0
                  ? colors.successBg
                  : colors.lossBg,
            borderRadius: radii.md,
          },
        ]}
      >
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={[typography.caption, { color: colors.textMuted }]}>
            Potencjalny wynik operacyjny
          </Text>
          <Text
            style={[
              typography.money,
              {
                color:
                  profit === null
                    ? colors.textMuted
                    : profit >= 0
                      ? colors.success
                      : colors.loss,
                fontVariant: ['tabular-nums'],
              },
            ]}
          >
            {profit === null ? 'Brak wyceny' : formatSignedMoneyMinor(profit)}
          </Text>
        </View>
        <Badge
          label={`ROI ${formatRoiBps(item.hasValuation ? item.roiBps : null)}`}
          tone={profit === null ? 'neutral' : profit >= 0 ? 'success' : 'danger'}
        />
      </View>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <Ionicons
          name="sparkles-outline"
          size={15}
          color={colors.accent}
          style={{ marginTop: 2 }}
        />
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={[typography.caption, { color: colors.accent, fontWeight: '600' }]}>
            {insight.label}
          </Text>
          <Text
            style={[typography.caption, { color: colors.textMuted }]}
            numberOfLines={2}
          >
            {insight.text}
          </Text>
        </View>
      </View>
      <View style={[styles.footer, { borderTopColor: colors.border }]}>
        <Text style={[typography.caption, { color: colors.textSubtle, flex: 1 }]}>
          {formatRelativeSync(item.verifiedAt)}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Zobacz szczegóły: ${item.title}`}
          onPress={onPress}
          style={({ pressed }) => ({
            flexDirection: 'row',
            alignItems: 'center',
            gap: 6,
            minHeight: 44,
            paddingLeft: 8,
            opacity: pressed ? 0.6 : 1,
          })}
        >
          <Text style={[typography.caption, { color: colors.accent, fontWeight: '700' }]}>
            Zobacz szczegóły
          </Text>
          <Ionicons name="arrow-forward" size={16} color={colors.accent} />
        </Pressable>
      </View>
    </View>
  );
}
const styles = StyleSheet.create({
  card: { borderWidth: 1, flex: 1 },
  top: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  summary: { flex: 1, flexDirection: 'row', gap: 12, minWidth: 0 },
  thumb: {
    width: 72,
    height: 80,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  image: { width: '100%', height: '100%' },
  badges: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  prices: { flexDirection: 'row', gap: 12 },
  profit: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    padding: 12,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    paddingTop: 4,
    marginBottom: -8,
  },
});
