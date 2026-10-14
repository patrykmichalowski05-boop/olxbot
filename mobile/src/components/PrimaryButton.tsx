import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  ViewStyle,
} from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';
import { touchTarget } from '@/theme/tokens';

type Props = {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
  style?: ViewStyle;
};

export function PrimaryButton({
  label,
  onPress,
  disabled,
  loading,
  variant = 'primary',
  style,
}: Props) {
  const { colors, radii, spacing, typography } = useTheme();

  const background =
    variant === 'primary'
      ? colors.accent
      : variant === 'secondary'
        ? colors.surfaceElevated
        : 'transparent';

  const textColor =
    variant === 'primary' ? colors.background : colors.text;

  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor: background,
          borderRadius: radii.md,
          borderColor: colors.border,
          borderWidth: variant === 'secondary' ? 1 : 0,
          opacity: pressed || disabled ? 0.75 : 1,
          minHeight: touchTarget,
          paddingHorizontal: spacing.lg,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <Text style={[typography.bodyStrong, { color: textColor, textAlign: 'center' }]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
