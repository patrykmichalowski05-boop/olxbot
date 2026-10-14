import React, { useRef, useState } from 'react';
import { Text } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useForm, Controller, useWatch } from 'react-hook-form';
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
import { isPostgresUuid } from '@/utils/identifiers';
import { Panel } from '@/components/Panel';
import { DemoBanner } from '@/components/DemoBanner';
import { useQueryClient } from '@tanstack/react-query';

const schema = z.object({
  amount: z.string().min(1, 'Podaj kwotę zakupu'),
  note: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function PurchaseScreen() {
  const { listingId } = useLocalSearchParams<{ listingId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { colors, spacing, typography } = useTheme();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingMinor, setPendingMinor] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const idempotencyRef = useRef<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { amount: '', note: '' },
  });
  const amount = useWatch({ control, name: 'amount' });

  const canUseLiveDeals = api.mode === 'live' && Boolean(workspaceId()) && isPostgresUuid(listingId);

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
        await queryClient.invalidateQueries({ queryKey: ['deals'] });
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
      await queryClient.invalidateQueries({ queryKey: ['deals'] });
      router.replace('/flips');
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
      setConfirmOpen(false);
    }
  };

  const summary = pendingMinor ?? parseMoneyInput(amount || '');

  return (
    <AppScreen scroll maxWidth={800}>
      <Header title="Zapis zakupu" showBack />
      <DemoBanner />
      <Text style={[typography.body, { color: colors.textMuted, marginBottom: spacing.lg }]}>
        Zapis finansowy wymaga potwierdzenia. Otwarcie ogłoszenia nie oznacza zakupu.
      </Text>

      <Panel title="Dane zakupu">
      {api.mode === 'live' && !canUseLiveDeals ? <Text style={[typography.caption, { color: colors.risk }]}>Brak powiązania oferty z rejestrem flipów lub przestrzeni transakcji. Zapis zakupu jest niedostępny.</Text> : null}
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
          <FormField label="Notatka robocza" hint="Nie jest wysyłana z zakupem." value={value} onChangeText={onChange} />
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

      <PrimaryButton label="Podsumuj i zapisz" onPress={onReview} disabled={api.mode === 'live' && !canUseLiveDeals} />
      </Panel>

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
