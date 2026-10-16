import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'expo-router';
import { api } from '@/api';
import type { ManualAnalysisResult } from '@/api/endpoints/universal';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { Badge } from '@/components/Badge';
import { DecisionBadge } from '@/components/DecisionBadge';
import { DemoBanner } from '@/components/DemoBanner';
import { ErrorState } from '@/components/ErrorState';
import { FormField } from '@/components/FormField';
import { Header } from '@/components/Header';
import type { IconName } from '@/components/IconButton';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useTheme } from '@/theme/ThemeProvider';
import { layout } from '@/theme/tokens';
import { radarSource } from '@/utils/config';
import { parseMoneyInput } from '@/utils/money';

const schema = z.object({
  linkOrTitle: z.string().trim().min(3, 'Podaj link lub tytuł ogłoszenia.'),
  price: z
    .string()
    .min(1, 'Podaj cenę.')
    .refine(
      (value) => (parseMoneyInput(value) ?? 0) > 0,
      'Podaj poprawną cenę większą od zera.',
    ),
  category: z.enum(['ELECTRONICS', 'CAR', 'FASHION']),
  description: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;
const categories: { id: FormValues['category']; label: string; icon: IconName }[] = [
  { id: 'ELECTRONICS', label: 'Elektronika', icon: 'hardware-chip-outline' },
  { id: 'CAR', label: 'Auta', icon: 'car-sport-outline' },
  { id: 'FASHION', label: 'Moda', icon: 'shirt-outline' },
];
const steps: { icon: IconName; title: string; text: string }[] = [
  {
    icon: 'document-text-outline',
    title: 'Dodaj dane oferty',
    text: 'Tytuł, cena i opis pomagają rozpoznać przedmiot.',
  },
  {
    icon: 'stats-chart-outline',
    title: 'Sprawdź potencjał',
    text: 'Analiza oceni dostępne dane i możliwości odsprzedaży.',
  },
  {
    icon: 'shield-checkmark-outline',
    title: 'Podejmij decyzję',
    text: 'Sprawdź wynik i ryzyka, zanim zdecydujesz się na zakup.',
  },
];
export default function AnalyzeScreen() {
  const router = useRouter();
  const { colors, spacing, typography, radii } = useTheme();
  const [jobId, setJobId] = useState<string | null>(null);
  const [stage, setStage] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<ManualAnalysisResult | null>(null);
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      linkOrTitle: '',
      price: '',
      category: 'ELECTRONICS',
      description: '',
    },
  });

  useEffect(() => {
    if (!jobId || stage !== 'running') return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    const poll = async () => {
      try {
        const job = await api.analyze.pollJob(jobId);
        if (!alive) return;
        if (job.status === 'done') {
          setResult(job.result ?? null);
          setStage('done');
          setMessage('Analiza zakończona.');
        } else if (job.status === 'error' || Date.now() - started > 90_000) {
          setStage('error');
          setMessage('Analiza nie została zakończona. Spróbuj ponownie za chwilę.');
        } else
          timer = setTimeout(() => {
            void poll();
          }, 800);
      } catch (error) {
        if (alive) {
          setStage('error');
          setMessage(apiErrorMessage(error));
        }
      }
    };
    timer = setTimeout(() => {
      void poll();
    }, 800);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [jobId, stage]);

  const onSubmit = handleSubmit(async (values) => {
    setStage('running');
    setJobId(null);
    setResult(null);
    setMessage('Sprawdzamy dane oferty i przygotowujemy ocenę.');
    try {
      const response = await api.analyze.submitManual({
        external_id: values.linkOrTitle.slice(0, 120),
        title: values.linkOrTitle.slice(0, 500),
        price: values.price,
        category: values.category,
        description: values.description,
      });
      if ('result' in response && response.result) {
        setResult(response.result);
        setStage('done');
        setMessage('Analiza zakończona.');
      } else if ('job_id' in response) setJobId(response.job_id);
      else {
        setStage('done');
        setMessage('Analiza zakończona.');
      }
    } catch (error) {
      setStage('error');
      setMessage(apiErrorMessage(error));
    }
  });
  const detailId =
    api.mode === 'live' && result
      ? result.listing_id
        ? String(result.listing_id)
        : result.snapshot_id && radarSource() === 'universal'
          ? `snap-${result.snapshot_id}`
          : null
      : null;
  return (
    <AppScreen scroll bottomInset={false}>
      <View
        style={{
          width: '100%',
          maxWidth: layout.formMaxWidth,
          alignSelf: 'center',
          gap: spacing.lg,
        }}
      >
        <View>
          <Header title="Analiza oferty" subtitle="Oceń potencjał przed zakupem." />
          <DemoBanner />
        </View>
        <View
          style={[
            styles.panel,
            {
              borderRadius: radii.xxl,
              borderColor: colors.accentMuted,
              backgroundColor: colors.accentBg,
              padding: spacing.section,
            },
          ]}
        >
          <Badge
            label="Twoja przewaga przy zakupie"
            icon="sparkles-outline"
            tone="accent"
          />
          <Text
            style={[typography.headline, { color: colors.text, marginTop: spacing.md }]}
          >
            Dobra decyzja zaczyna się od danych.
          </Text>
          <Text
            style={[typography.body, { color: colors.textMuted, marginTop: spacing.sm }]}
          >
            Dodaj ofertę i sprawdź, czy warto przyjrzeć się jej bliżej.
          </Text>
        </View>
        <View
          style={[
            styles.panel,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              borderRadius: radii.xxl,
              padding: spacing.section,
            },
          ]}
        >
          <Text
            style={[
              typography.label,
              { color: colors.textMuted, marginBottom: spacing.lg },
            ]}
          >
            DANE OGŁOSZENIA
          </Text>
          <Controller
            control={control}
            name="category"
            render={({ field: { value, onChange } }) => (
              <View style={{ marginBottom: spacing.lg, gap: spacing.sm }}>
                <Text style={[typography.bodyStrong, { color: colors.text }]}>
                  Kategoria
                </Text>
                <View style={styles.categories}>
                  {categories.map((category) => {
                    const active = value === category.id;
                    return (
                      <Pressable
                        key={category.id}
                        accessibilityRole="button"
                        accessibilityLabel={category.label}
                        accessibilityState={{ selected: active }}
                        aria-selected={active}
                        onPress={() => onChange(category.id)}
                        disabled={stage === 'running'}
                        style={({ pressed }) => ({
                          flexDirection: 'row',
                          alignItems: 'center',
                          minHeight: 44,
                          gap: 6,
                          paddingHorizontal: 12,
                          paddingVertical: 12,
                          borderWidth: 1,
                          borderColor: active ? colors.accentMuted : colors.border,
                          borderRadius: radii.md,
                          backgroundColor: active ? colors.accentBg : colors.background,
                          opacity: pressed ? 0.7 : 1,
                        })}
                      >
                        <Ionicons
                          name={category.icon}
                          size={16}
                          color={active ? colors.accent : colors.textMuted}
                        />
                        <Text
                          style={[
                            typography.caption,
                            {
                              color: active ? colors.accent : colors.textMuted,
                              fontWeight: '600',
                            },
                          ]}
                        >
                          {category.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>
              </View>
            )}
          />
          <Controller
            control={control}
            name="linkOrTitle"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Link lub tytuł ogłoszenia"
                placeholder="Np. iPhone 14 Pro 256 GB"
                hint="Dla linku dopisz model i stan w opisie."
                autoCapitalize="none"
                autoCorrect={false}
                value={value}
                onChangeText={onChange}
                onBlur={onBlur}
                error={errors.linkOrTitle?.message}
                editable={stage !== 'running'}
              />
            )}
          />
          <Controller
            control={control}
            name="price"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Cena zakupu (zł)"
                placeholder="Np. 1500,00"
                keyboardType="decimal-pad"
                value={value}
                onChangeText={onChange}
                onBlur={onBlur}
                error={errors.price?.message}
                editable={stage !== 'running'}
              />
            )}
          />
          <Controller
            control={control}
            name="description"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Opis i specyfikacja"
                hint="Opcjonalnie. Więcej szczegółów pomaga trafniej ocenić ofertę."
                placeholder="Model, pamięć, stan, akcesoria, znane usterki…"
                multiline
                numberOfLines={4}
                value={value}
                onChangeText={onChange}
                onBlur={onBlur}
                style={{ minHeight: 120, textAlignVertical: 'top' }}
                editable={stage !== 'running'}
              />
            )}
          />
          <PrimaryButton
            label={stage === 'running' ? 'Analiza w toku…' : 'Przeanalizuj ofertę'}
            icon="sparkles-outline"
            onPress={onSubmit}
            loading={stage === 'running'}
          />
          <Text
            style={[
              typography.caption,
              { color: colors.textSubtle, marginTop: spacing.md, textAlign: 'center' },
            ]}
          >
            Prognoza wspiera ocenę oferty. Wynik zależy od stanu przedmiotu i kosztów
            transakcji.
          </Text>
        </View>
        {stage === 'error' ? (
          <ErrorState
            title="Nie udało się przeanalizować oferty"
            message={message}
            onRetry={onSubmit}
          />
        ) : null}
        {stage === 'running' || stage === 'done' ? (
          <View
            accessibilityLiveRegion="polite"
            style={[
              styles.panel,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
                borderRadius: radii.xxl,
                padding: spacing.section,
                gap: spacing.md,
              },
            ]}
          >
            <Badge
              label={stage === 'done' ? 'Analiza gotowa' : 'Przygotowujemy ocenę'}
              icon={stage === 'done' ? 'checkmark-circle-outline' : 'hourglass-outline'}
              tone={stage === 'done' ? 'success' : 'accent'}
            />
            <Text style={[typography.body, { color: colors.textMuted }]}>{message}</Text>
            {result ? <DecisionBadge decision={result.decision} /> : null}
            {detailId ? (
              <PrimaryButton
                label="Zobacz szczegóły analizy"
                variant="secondary"
                icon="arrow-forward"
                onPress={() =>
                  router.push({ pathname: '/offer/[id]', params: { id: detailId } })
                }
              />
            ) : null}
          </View>
        ) : null}
        <View style={{ gap: spacing.lg, padding: spacing.sm }}>
          <Text style={[typography.headline, { color: colors.text }]}>
            Jak działa analiza?
          </Text>
          {steps.map((step, index) => (
            <View key={step.title} style={styles.step}>
              <View
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: radii.md,
                  backgroundColor: colors.accentBg,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Ionicons name={step.icon} size={19} color={colors.accent} />
              </View>
              <View style={{ flex: 1, gap: 4 }}>
                <Text style={[typography.bodyStrong, { color: colors.text }]}>
                  {index + 1}. {step.title}
                </Text>
                <Text style={[typography.caption, { color: colors.textMuted }]}>
                  {step.text}
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>
    </AppScreen>
  );
}
const styles = StyleSheet.create({
  panel: { borderWidth: 1 },
  categories: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  step: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
});
