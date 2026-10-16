import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useTheme } from '@/theme/ThemeProvider';

type Props = {
  title: string;
  items: string[];
  emptyLabel?: string;
};

export function RiskList({ title, items, emptyLabel = 'Brak pozycji' }: Props) {
  const { colors, spacing, typography } = useTheme();

  return (
    <View style={{ gap: spacing.sm }}>
      <Text style={[typography.bodyStrong, { color: colors.text }]}>{title}</Text>
      {items.length === 0 ? (
        <Text style={[typography.body, { color: colors.textMuted }]}>{emptyLabel}</Text>
      ) : (
        items.map((item) => (
          <View key={item} style={styles.row}>
            <Ionicons name="alert-circle-outline" size={16} color={colors.risk} />
            <Text style={[typography.body, { color: colors.text, flex: 1 }]}>{item}</Text>
          </View>
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
});
