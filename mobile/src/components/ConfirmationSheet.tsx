import React from 'react';
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { useTheme } from '@/theme/ThemeProvider';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { PrimaryButton } from './PrimaryButton';

type Props = {
  visible: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  children?: React.ReactNode;
};

export function ConfirmationSheet({
  visible,
  title,
  description,
  confirmLabel = 'Potwierdź',
  onConfirm,
  onCancel,
  loading,
  children,
}: Props) {
  const { colors, radii, spacing, typography } = useTheme();
  const { isMobile } = useResponsiveLayout();

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Pressable style={[styles.backdrop, { backgroundColor: colors.overlay, justifyContent: isMobile ? 'flex-end' : 'center' }]} onPress={loading ? undefined : onCancel}>
        <Pressable
          onPress={event => event.stopPropagation()}
          style={[
            styles.sheet,
            {
              backgroundColor: colors.surface,
              borderRadius: radii.lg,
              padding: spacing.lg,
              gap: spacing.md,
              borderColor: colors.border,
            },
          ]}
        >
          <Text style={[typography.headline, { color: colors.text }]}>{title}</Text>
          <Text style={[typography.body, { color: colors.textMuted }]}>{description}</Text>
          {children ? <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ gap: spacing.sm }}>{children}</ScrollView> : null}
          <PrimaryButton label={confirmLabel} onPress={onConfirm} loading={loading} />
          <PrimaryButton label="Anuluj" onPress={onCancel} variant="ghost" disabled={loading} />
        </Pressable>
      </Pressable>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    padding: 16,
  },
  sheet: { marginBottom: 8, width: '100%', maxWidth: 560, maxHeight: '92%', borderWidth: 1, alignSelf: 'center' },
});
