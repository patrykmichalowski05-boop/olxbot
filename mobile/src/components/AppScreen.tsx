import React from 'react';
import { ScrollView, StyleSheet, View, ViewProps } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTheme } from '@/theme/ThemeProvider';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';

type Props = ViewProps & {
  scroll?: boolean;
  padded?: boolean;
  children: React.ReactNode;
  maxWidth?: number;
};

export function AppScreen({
  scroll = false,
  padded = true,
  children,
  style,
  maxWidth = 1600,
  ...rest
}: Props) {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const { isMobile, pagePadding } = useResponsiveLayout();

  const content = (
    <View
      style={[
        styles.inner,
        { maxWidth, paddingHorizontal: isMobile ? (padded ? spacing.lg : 0) : (padded ? pagePadding : pagePadding - spacing.lg) },
        { paddingBottom: (isMobile ? insets.bottom : 0) + spacing.lg },
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );

  return (
    <View style={[styles.root, { backgroundColor: colors.background, paddingTop: isMobile ? insets.top + spacing.sm : spacing.xl }]}>
      {scroll ? (
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.scrollGrow}>
          {content}
        </ScrollView>
      ) : (
        content
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, minHeight: 0, minWidth: 0 },
  inner: { flex: 1, width: '100%', alignSelf: 'center', minWidth: 0, minHeight: 0 },
  scrollGrow: { flexGrow: 1 },
});
