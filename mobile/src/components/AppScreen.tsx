import React from 'react';
import { ScrollView, StyleSheet, View, ViewProps } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTheme } from '@/theme/ThemeProvider';

type Props = ViewProps & {
  scroll?: boolean;
  padded?: boolean;
  children: React.ReactNode;
};

export function AppScreen({
  scroll = false,
  padded = true,
  children,
  style,
  ...rest
}: Props) {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();

  const content = (
    <View
      style={[
        styles.inner,
        padded && { paddingHorizontal: spacing.lg },
        { paddingBottom: insets.bottom + spacing.lg },
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );

  return (
    <View style={[styles.root, { backgroundColor: colors.background, paddingTop: insets.top }]}>
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
  root: { flex: 1 },
  inner: { flex: 1 },
  scrollGrow: { flexGrow: 1 },
});
