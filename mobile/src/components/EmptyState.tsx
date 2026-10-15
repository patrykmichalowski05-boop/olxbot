import React from 'react';
import { Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/theme/ThemeProvider';
import { PrimaryButton } from './PrimaryButton';
import type { IconName } from './IconButton';

type Props = {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: IconName;
};
export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  icon = 'radio-outline',
}: Props) {
  const { colors, spacing, typography, radii } = useTheme();
  return (
    <View
      style={{
        alignItems: 'center',
        paddingVertical: spacing.xxl,
        paddingHorizontal: spacing.section,
        gap: spacing.lg,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radii.xxl,
        backgroundColor: colors.surface,
      }}
    >
      <View
        style={{
          width: 72,
          height: 72,
          borderRadius: radii.xxl,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.accentBg,
        }}
      >
        <Ionicons name={icon} size={30} color={colors.accent} />
      </View>
      <View style={{ gap: spacing.sm, maxWidth: 380 }}>
        <Text style={[typography.headline, { color: colors.text, textAlign: 'center' }]}>
          {title}
        </Text>
        {description ? (
          <Text
            style={[typography.body, { color: colors.textMuted, textAlign: 'center' }]}
          >
            {description}
          </Text>
        ) : null}
      </View>
      {actionLabel && onAction ? (
        <PrimaryButton label={actionLabel} onPress={onAction} icon="arrow-forward" />
      ) : null}
    </View>
  );
}
