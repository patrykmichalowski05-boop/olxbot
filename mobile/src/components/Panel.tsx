import React from 'react';
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';

export function Panel({ title, subtitle, right, children, style }: {
  title?: string; subtitle?: string; right?: React.ReactNode; children: React.ReactNode; style?: StyleProp<ViewStyle>;
}) {
  const { colors, typography } = useTheme();
  return <View style={[styles.panel, { backgroundColor: colors.surface, borderColor: colors.border }, style]}>
    {title || right ? <View style={styles.heading}>
      <View style={{ flex: 1, minWidth: 0, gap: 4 }}>
        {title ? <Text style={[typography.headline, { color: colors.text }]}>{title}</Text> : null}
        {subtitle ? <Text style={[typography.caption, { color: colors.textMuted }]}>{subtitle}</Text> : null}
      </View>
      {right}
    </View> : null}
    {children}
  </View>;
}

const styles = StyleSheet.create({
  panel: { borderWidth: 1, borderRadius: 16, padding: 20, gap: 16, minWidth: 0 },
  heading: { flexDirection: 'row', alignItems: 'center', gap: 12 },
});
