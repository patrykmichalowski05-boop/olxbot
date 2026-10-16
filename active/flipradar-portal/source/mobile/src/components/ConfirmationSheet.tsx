import React from 'react';
import { Modal, Pressable, StyleSheet, Text } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';
import { PrimaryButton } from './PrimaryButton';

type Props = {
  visible: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
};

export function ConfirmationSheet({
  visible,
  title,
  description,
  confirmLabel = 'Potwierdź',
  onConfirm,
  onCancel,
  loading,
}: Props) {
  const { colors, radii, spacing, typography } = useTheme();

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable style={[styles.backdrop, { backgroundColor: colors.overlay }]} onPress={onCancel}>
        <Pressable
          style={[
            styles.sheet,
            {
              backgroundColor: colors.surface,
              borderRadius: radii.lg,
              padding: spacing.lg,
              gap: spacing.md,
            },
          ]}
        >
          <Text style={[typography.headline, { color: colors.text }]}>{title}</Text>
          <Text style={[typography.body, { color: colors.textMuted }]}>{description}</Text>
          <PrimaryButton label={confirmLabel} onPress={onConfirm} loading={loading} />
          <PrimaryButton label="Anuluj" onPress={onCancel} variant="ghost" />
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    padding: 16,
  },
  sheet: { marginBottom: 8 },
});
