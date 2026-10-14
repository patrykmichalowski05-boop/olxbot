import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';
import { PrimaryButton } from './PrimaryButton';

type Props = {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ title, description, actionLabel, onAction }: Props) {
  const { colors, spacing, typography } = useTheme();

  return (
    <View style={[styles.wrap, { paddingVertical: spacing.xxl, gap: spacing.md }]}>
      <Text style={[typography.headline, { color: colors.text, textAlign: 'center' }]}>
        {title}
      </Text>
      {description ? (
        <Text style={[typography.body, { color: colors.textMuted, textAlign: 'center' }]}>
          {description}
        </Text>
      ) : null}
      {actionLabel && onAction ? (
        <PrimaryButton label={actionLabel} onPress={onAction} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center' },
});
