import React, { useState } from 'react';
import { Image, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import type { OpportunityCard } from '@/features/opportunity/types';
import { useTheme } from '@/theme/ThemeProvider';

type Props = { item: OpportunityCard; style?: StyleProp<ViewStyle>; compact?: boolean };

export function ListingImage({ item, style, compact }: Props) {
  const { colors, typography } = useTheme();
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const icon = item.category === 'CAR' ? 'car-outline' : item.category === 'FASHION' ? 'shirt-outline' : item.category === 'ELECTRONICS' ? 'hardware-chip-outline' : 'cube-outline';

  return (
    <View style={[styles.image, { backgroundColor: colors.sidebar }, style]}>
      {item.imageUrl && failedUrl !== item.imageUrl ? (
        <Image accessibilityLabel={item.title} source={{ uri: item.imageUrl }} resizeMode="cover" style={StyleSheet.absoluteFill}
          onError={() => setFailedUrl(item.imageUrl ?? null)} />
      ) : (
        <View style={styles.placeholder}>
          <Ionicons name={icon} size={compact ? 24 : 32} color={colors.textMuted} />
          {!compact ? <Text style={[typography.caption, { color: colors.textMuted }]}>Brak zdjęcia</Text> : null}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  image: { overflow: 'hidden', alignItems: 'center', justifyContent: 'center' },
  placeholder: { gap: 8, alignItems: 'center' },
});
