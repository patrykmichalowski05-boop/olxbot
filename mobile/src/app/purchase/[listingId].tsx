import React, { useMemo, useRef, useState } from 'react';
import { Text } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { ConfirmationSheet } from '@/components/ConfirmationSheet';
import { FormField } from '@/components/FormField';
import { Header } from '@/components/Header';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useTheme } from '@/theme/ThemeProvider';
import { createIdempotencyKey } from '@/utils/idempotency';
import { formatMoneyMinor, parseMoneyInput } from '@/utils/money';
import { workspaceId } from '@/utils/config';

const schema = z.object({
  amount: z.string().min(1, 'Podaj kwotę zakupu'),
  note: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function PurchaseScreen() {
  const { listingId } = useLocalSearchParams<{ listingId: string }>();
  const router = useRouter();
  const { colors, spacing, typography } = useTheme();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingMinor, setPendingMinor] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const idempotencyRef = useRef<string | null>(null);

  const {
    control,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { amount: '', note: '' },
  });

  const canUseLiveDeals = api.mode === 'live' && Boolean(workspaceId());

  const onReview = handleSubmit((values) => {
    const minor = parseMoneyInput(values.amount);
    if (minor === null) {
      setError('Nieprawidłowa kwota');
      return;
    }
    setError('');
    setPendingMinor(minor);
    setConfirmOpen(true);
  });

  const onConfirm = async () => {
    if (pendingMinor === null) return;
    setLoading(true);
    setError('');
    if (!idempotencyRef.current) {
      idempotencyRef.current = createIdempotencyKey('purchase');
    }
    try {
      if (api.mode === 'demo') {
        const demo = await import('@/api/demo/demoClient');
        demo.demoClient.recordPurchase(String(listingId), pendingMinor);
        router.replace('/flips');
        return;
      }
      if (!canUseLiveDeals) {
        throw new Error('Skonfiguruj workspace i backend PostgreSQL (API v2).');
      }
      await api.deals.purchase({
        listingId: String(listingId),
        amountMinor: pendingMinor,
        idempotencyKey: idempotencyRef.current,
      });
      router.replace('/flips');
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
      setConfirmOpen(false);
    }
  };

  const summary = useMemo(() => {
    const minor = pendingMinor ?? parseMoneyInput(getValues('amount') || '');
    return minor;
  }, [pendingMinor, getValues]);

  return (
    <AppScreen scroll>
      <Header title="Zapis zakupu" showBack />
      <Text style={[typography.body, { color: colors.textMuted, marginBottom: spacing.lg }]}>
        Zapis finansowy wymaga potwierdzenia. Otwarcie ogłoszenia nie oznacza zakupu.
      </Text>

      <Controller
        control={control}
        name="amount"
        render={({ field: { onChange, value } }) => (
          <FormField
            label="Kwota zakupu (zł)"
            keyboardType="decimal-pad"
            value={value}
            onChangeText={onChange}
            error={errors.amount?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="note"
        render={({ field: { onChange, value } }) => (
          <FormField label="Notatka (lokalnie)" value={value} onChangeText={onChange} />
        )}
      />

      {summary !== null && summary !== undefined ? (
        <Text style={[typography.bodyStrong, { color: colors.text, marginBottom: spacing.md }]}>
          Zapiszesz zakup: {formatMoneyMinor(summary)}
        </Text>
      ) : null}

      {error ? (
        <Text style={[typography.caption, { color: colors.loss, marginBottom: spacing.sm }]}>
          {error}
        </Text>
      ) : null}

      <PrimaryButton label="Podsumuj i zapisz" onPress={onReview} />

      <ConfirmationSheet
        visible={confirmOpen}
        title="Potwierdź zapis zakupu"
        description={`Czy na pewno zapisać zakup ${formatMoneyMinor(pendingMinor)} dla oferty ${listingId}?`}
        confirmLabel="Zapisz zakup"
        loading={loading}
        onConfirm={() => void onConfirm()}
        onCancel={() => setConfirmOpen(false)}
      />
    </AppScreen>
  );
}
