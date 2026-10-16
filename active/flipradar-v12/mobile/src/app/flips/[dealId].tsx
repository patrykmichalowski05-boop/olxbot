import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { ConfirmationSheet } from '@/components/ConfirmationSheet';
import { ErrorState } from '@/components/ErrorState';
import { FormField } from '@/components/FormField';
import { Header } from '@/components/Header';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { MoneyValue } from '@/components/MoneyValue';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useTheme } from '@/theme/ThemeProvider';
import { createIdempotencyKey } from '@/utils/idempotency';
import { formatMoneyMinor, parseMoneyInput } from '@/utils/money';
import { workspaceId } from '@/utils/config';

const costSchema = z.object({ kind: z.string().min(1), amount: z.string().min(1) });
const saleSchema = z.object({ amount: z.string().min(1) });

export default function DealDetailScreen() {
  const { dealId } = useLocalSearchParams<{ dealId: string }>();
  const queryClient = useQueryClient();
  const { colors, spacing, typography } = useTheme();
  const [sheet, setSheet] = useState<'cost' | 'sale' | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const idempotencyRef = useRef<string | null>(null);

  const dealQuery = useQuery({
    queryKey: ['deal', dealId, api.mode],
    queryFn: () => api.deals.get(String(dealId)),
  });

  const costForm = useForm<z.infer<typeof costSchema>>({
    resolver: zodResolver(costSchema),
    defaultValues: { kind: 'prep', amount: '' },
  });

  const saleForm = useForm<z.infer<typeof saleSchema>>({
    resolver: zodResolver(saleSchema),
    defaultValues: { amount: '' },
  });

  if (dealQuery.isLoading) {
    return (
      <AppScreen>
        <LoadingSkeleton rows={2} />
      </AppScreen>
    );
  }

  if (dealQuery.isError || !dealQuery.data) {
    return (
      <AppScreen>
        <ErrorState message={apiErrorMessage(dealQuery.error)} onRetry={() => dealQuery.refetch()} />
      </AppScreen>
    );
  }

  const deal = dealQuery.data;

  const submitFinancial = async (
    kind: 'cost' | 'sale',
    values: { amount: string; kind?: string },
  ) => {
    const minor = parseMoneyInput(values.amount);
    if (minor === null) {
      setError('Nieprawidłowa kwota');
      return;
    }
    setLoading(true);
    setError('');
    if (!idempotencyRef.current) {
      idempotencyRef.current = createIdempotencyKey(kind);
    }
    try {
      if (api.mode === 'live' && workspaceId()) {
        if (kind === 'cost') {
          await api.deals.cost({
            dealId: String(dealId),
            kind: values.kind ?? 'misc',
            amountMinor: minor,
            idempotencyKey: idempotencyRef.current,
          });
        } else {
          await api.deals.sell({
            dealId: String(dealId),
            amountMinor: minor,
            idempotencyKey: idempotencyRef.current,
          });
        }
      } else if (api.mode === 'demo') {
        // demo: brak osobnego silnika — odśwież listę
      } else {
        throw new Error('API v2 niedostępne');
      }
      idempotencyRef.current = null;
      setSheet(null);
      await queryClient.invalidateQueries({ queryKey: ['deals'] });
      await queryClient.invalidateQueries({ queryKey: ['deal', dealId] });
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppScreen scroll>
      <Header title={deal.title ?? 'Flip'} showBack showNotifications={false} />

      <View style={{ gap: spacing.md, marginBottom: spacing.lg }}>
        <Text style={[typography.caption, { color: colors.textMuted }]}>
          Status: {deal.status ?? '—'}
        </Text>
        <MoneyValue label="Zakup" amountMinor={deal.purchase_minor ?? null} emphasize />
        <MoneyValue label="Koszty łącznie" amountMinor={deal.cost_minor ?? null} />
        <MoneyValue label="Sprzedaż" amountMinor={deal.sale_minor ?? null} />
        <MoneyValue label="Wynik" amountMinor={deal.realized_profit_minor ?? null} />
      </View>

      <PrimaryButton label="Dodaj koszt" variant="secondary" onPress={() => setSheet('cost')} />
      <View style={{ height: spacing.sm }} />
      {deal.status !== 'SOLD' ? (
        <PrimaryButton label="Zapisz sprzedaż" onPress={() => setSheet('sale')} />
      ) : null}

      {error ? (
        <Text style={[typography.caption, { color: colors.loss, marginTop: spacing.md }]}>
          {error}
        </Text>
      ) : null}

      <ConfirmationSheet
        visible={sheet === 'cost'}
        title="Dodaj koszt"
        description="Podaj rodzaj i kwotę kosztu przygotowania."
        confirmLabel="Zapisz koszt"
        loading={loading}
        onConfirm={() => { void costForm.handleSubmit((v) => submitFinancial('cost', v))(); }}
        onCancel={() => setSheet(null)}
      />

      {sheet === 'cost' ? (
        <View>
          <Controller
            control={costForm.control}
            name="kind"
            render={({ field: { onChange, value } }) => (
              <FormField label="Rodzaj kosztu" value={value} onChangeText={onChange} />
            )}
          />
          <Controller
            control={costForm.control}
            name="amount"
            render={({ field: { onChange, value } }) => (
              <FormField
                label="Kwota (zł)"
                keyboardType="decimal-pad"
                value={value}
                onChangeText={onChange}
              />
            )}
          />
        </View>
      ) : null}

      <ConfirmationSheet
        visible={sheet === 'sale'}
        title="Zapis sprzedaży"
        description={`Potwierdź kwotę sprzedaży (${formatMoneyMinor(parseMoneyInput(saleForm.getValues('amount')) ?? null)}).`}
        confirmLabel="Zapisz sprzedaż"
        loading={loading}
        onConfirm={() => { void saleForm.handleSubmit((v) => submitFinancial('sale', v))(); }}
        onCancel={() => setSheet(null)}
      />

      {sheet === 'sale' ? (
        <Controller
          control={saleForm.control}
          name="amount"
          render={({ field: { onChange, value } }) => (
            <FormField
              label="Kwota sprzedaży (zł)"
              keyboardType="decimal-pad"
              value={value}
              onChangeText={onChange}
            />
          )}
        />
      ) : null}
    </AppScreen>
  );
}
