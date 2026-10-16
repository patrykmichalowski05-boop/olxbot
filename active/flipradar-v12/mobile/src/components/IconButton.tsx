import React from 'react';
import { ActivityIndicator, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/theme/ThemeProvider';
import { touchTarget } from '@/theme/tokens';

export type IconName = React.ComponentProps<typeof Ionicons>['name'];

export function IconButton({
  icon,
  label,
  onPress,
  active = false,
  loading = false,
  disabled = false,
}: {
  icon: IconName;
  label: string;
  onPress: () => void;
  active?: boolean;
  loading?: boolean;
  disabled?: boolean;
}) {
  const { colors, radii } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{
        disabled: disabled || loading,
        busy: loading,
        selected: active,
      }}
      aria-busy={Boolean(loading)}
      aria-disabled={disabled || loading}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => ({
        minWidth: touchTarget,
        minHeight: touchTarget,
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: radii.md,
        borderWidth: 1,
        borderColor: active ? colors.accentMuted : colors.border,
        backgroundColor: active ? colors.accentBg : colors.surface,
        opacity: pressed || disabled ? 0.6 : 1,
      })}
    >
      {loading ? (
        <ActivityIndicator size="small" color={colors.accent} />
      ) : (
        <Ionicons
          name={icon}
          size={19}
          color={active ? colors.accent : colors.textMuted}
        />
      )}
    </Pressable>
  );
}
