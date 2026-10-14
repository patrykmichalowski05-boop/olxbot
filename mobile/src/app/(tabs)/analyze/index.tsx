import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'expo-router';
import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import type { ManualAnalysisResult } from '@/api/endpoints/universal';
import { AppScreen } from '@/components/AppScreen';
import { DecisionBadge } from '@/components/DecisionBadge';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { FormField } from '@/components/FormField';
import { Header } from '@/components/Header';
import { Panel } from '@/components/Panel';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';
import { parseMoneyInput } from '@/utils/money';

const schema = z.object({
  linkOrTitle: z.string().min(3, 'Podaj link lub tytuł'),
  price: z.string().refine(value => parseMoneyInput(value) !== null, 'Podaj prawidłową cenę'),
  category: z.enum(['ELECTRONICS', 'CAR', 'FASHION']),
  description: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function AnalyzeScreen() {
  const router = useRouter();
  const { colors, typography } = useTheme();
  const { isMobile } = useResponsiveLayout();
  const [jobId, setJobId] = useState<string | null>(null);
  const [stage, setStage] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<ManualAnalysisResult | null>(null);
  const { control, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema), defaultValues: { linkOrTitle: '', price: '', category: 'ELECTRONICS', description: '' },
  });

  useEffect(() => {
    if (!jobId || stage !== 'running') return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const job = await api.analyze.pollJob(jobId);
        if (!alive) return;
        if (job.status === 'done') {
          setResult(job.result ?? null);
          setStage('done');
          setMessage(job.result ? 'Analiza zakończona.' : 'Brak wyniku analizy.');
        } else if (job.status === 'error') {
          setStage('error');
          setMessage('Analiza nie powiodła się.');
        } else {
          timer = setTimeout(() => void poll(), 800);
        }
      } catch (error) {
        if (alive) { setStage('error'); setMessage(apiErrorMessage(error)); }
      }
    };
    timer = setTimeout(() => void poll(), 800);
    return () => { alive = false; clearTimeout(timer); };
  }, [jobId, stage]);

  const onSubmit = handleSubmit(async values => {
    setJobId(null);
    setResult(null);
    setStage('running');
    setMessage('Trwa analiza oferty…');
    try {
      const response = await api.analyze.submitManual({
        external_id: values.linkOrTitle.slice(0, 120), title: values.linkOrTitle.slice(0, 500),
        price: values.price, category: values.category, description: values.description,
      });
      if ('result' in response && response.result) {
        setResult(response.result);
        setStage('done');
        setMessage('Analiza zakończona.');
      } else {
        setJobId(response.job_id);
      }
    } catch (error) { setStage('error'); setMessage(apiErrorMessage(error)); }
  });

  return <AppScreen scroll maxWidth={1300}>
    <Header title="Analiza AI" subtitle="Oceń przedmiot przed zakupem" />
    <DemoBanner />
    <View style={{ flexDirection: isMobile ? 'column' : 'row', alignItems: 'flex-start', gap: 20 }}>
      <Panel title="Dane oferty" subtitle="Podaj cenę i opis, aby otrzymać rekomendację." style={{ flex: isMobile ? undefined : 1, width: isMobile ? '100%' : undefined }}>
        <Controller control={control} name="linkOrTitle" render={({ field: { onChange, value } }) => <FormField label="Link lub tytuł ogłoszenia" value={value} onChangeText={onChange} error={errors.linkOrTitle?.message} placeholder="Np. iPhone 15 Pro 256 GB" />} />
        <Controller control={control} name="category" render={({ field: { onChange, value } }) => <View style={{ gap: 8 }}>
          <Text style={[typography.bodyStrong, { color: colors.text }]}>Kategoria</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
            {([['ELECTRONICS', 'Elektronika'], ['CAR', 'Auta'], ['FASHION', 'Moda']] as const).map(([id, label]) => <Pressable key={id} accessibilityRole="button" accessibilityState={{ selected: value === id }} onPress={() => onChange(id)} style={{ minHeight: 44, justifyContent: 'center', paddingHorizontal: 14, borderRadius: 10, backgroundColor: value === id ? colors.accentMuted : colors.background }}>
              <Text style={[typography.caption, { color: value === id ? colors.accent : colors.textMuted }]}>{label}</Text>
            </Pressable>)}
          </View>
        </View>} />
        <Controller control={control} name="price" render={({ field: { onChange, value } }) => <FormField label="Cena zakupu (zł)" keyboardType="decimal-pad" value={value} onChangeText={onChange} error={errors.price?.message} placeholder="0,00" />} />
        <Controller control={control} name="description" render={({ field: { onChange, value } }) => <FormField label="Opis / specyfikacja (opcjonalnie)" multiline numberOfLines={4} value={value} onChangeText={onChange} style={{ minHeight: 120, textAlignVertical: 'top' }} placeholder="Model, stan, wyposażenie, wady…" />} />
        <PrimaryButton label={stage === 'running' ? 'Analiza w toku…' : 'Wyślij do analizy'} onPress={onSubmit} loading={stage === 'running'} />
      </Panel>
      <Panel title="Wynik analizy" subtitle="Rekomendacja oraz uzasadnienie decyzji" style={{ flex: isMobile ? undefined : 1, width: isMobile ? '100%' : undefined }}>
        {stage === 'running' ? <View style={{ gap: 16, paddingVertical: 24, alignItems: 'center' }}><ActivityIndicator color={colors.accent} /><Text style={[typography.body, { color: colors.textMuted }]}>{message}</Text></View> :
          result ? <View style={{ gap: 16 }}>
            <DecisionBadge decision={result.decision} />
            <Text accessibilityLiveRegion="polite" style={[typography.caption, { color: colors.accent }]}>{message}</Text>
            {result.reasons?.length ? result.reasons.map((reason, index) => <Text key={index} style={[typography.body, { color: colors.text }]}>{reason}</Text>) : <Text style={[typography.body, { color: colors.textMuted }]}>Brak uzasadnienia decyzji.</Text>}
            <Text style={[typography.caption, { color: colors.textMuted }]}>Odpowiedź nie udostępnia wyceny odsprzedaży. Rekomendacja nie jest potwierdzeniem zysku.</Text>
            {result.listing_id ? <PrimaryButton label="Zobacz szczegóły oferty" variant="secondary" onPress={() => router.push({ pathname: '/offer/[id]', params: { id: String(result.listing_id) } })} /> : null}
          </View> : stage === 'error' ? <Text accessibilityRole="alert" style={[typography.body, { color: colors.loss }]}>{message}</Text> :
            <EmptyState title={stage === 'done' ? 'Brak wyniku' : 'Gotowe do analizy'} description={stage === 'done' ? message : 'Wypełnij formularz. Wynik pojawi się w tym miejscu.'} />}
      </Panel>
    </View>
  </AppScreen>;
}
