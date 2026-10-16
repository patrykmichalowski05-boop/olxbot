import React from 'react';
import { ScrollView, StyleSheet, View, ViewProps } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTheme } from '@/theme/ThemeProvider';
import { layout } from '@/theme/tokens';

type Props = ViewProps & {
  scroll?: boolean;
  padded?: boolean;
  bottomInset?: boolean;
  children: React.ReactNode;
};

export function AppScreen({
  scroll = false,
  padded = true,
  bottomInset = true,
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
        scroll ? { flexGrow: 1 } : { flex: 1 },
        padded && { paddingHorizontal: spacing.lg },
        { paddingBottom: spacing.lg + (bottomInset ? insets.bottom : 0) },
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );

  return (
    <View
      style={[
        styles.root,
        {
          backgroundColor: colors.background,
          paddingTop: insets.top + spacing.sm,
          paddingLeft: insets.left,
          paddingRight: insets.right,
        },
      ]}
    >
      {scroll ? (
        <ScrollView
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
          contentContainerStyle={styles.scrollGrow}
        >
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
  inner: { width: '100%', maxWidth: layout.contentMaxWidth, alignSelf: 'center' },
  scrollGrow: { flexGrow: 1 },
});
