import React from 'react';
import { Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/theme/ThemeProvider';
import { PrimaryButton } from './PrimaryButton';

type Props = {
  message: string;
  onRetry?: () => void;
  retrying?: boolean;
  title?: string;
};
export function ErrorState({
  message,
  onRetry,
  retrying,
  title = 'Nie udało się wczytać danych',
}: Props) {
  const { colors, spacing, typography, radii } = useTheme();
  return (
    <View
      accessibilityLiveRegion="polite"
      style={{
        alignItems: 'center',
        padding: spacing.xl,
        gap: spacing.lg,
        borderRadius: radii.xxl,
        backgroundColor: colors.surface,
        borderWidth: 1,
        borderColor: colors.border,
      }}
    >
      <View
        style={{
          width: 64,
          height: 64,
          borderRadius: radii.xl,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.warningBg,
        }}
      >
        <Ionicons name="cloud-offline-outline" size={28} color={colors.warning} />
      </View>
      <Text style={[typography.headline, { color: colors.text, textAlign: 'center' }]}>
        {title}
      </Text>
      <Text
        style={[
          typography.body,
          { color: colors.textMuted, textAlign: 'center', maxWidth: 380 },
        ]}
      >
        {message}
      </Text>
      {onRetry ? (
        <PrimaryButton
          label="Spróbuj ponownie"
          onPress={onRetry}
          loading={retrying}
          variant="secondary"
          icon="refresh-outline"
        />
      ) : null}
    </View>
  );
}
