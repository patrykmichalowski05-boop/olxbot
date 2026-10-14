import React, { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'expo-router';

import { api } from '@/api';
import { apiErrorMessage } from '@/api/errors';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { FormField } from '@/components/FormField';
import { Header } from '@/components/Header';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useTheme } from '@/theme/ThemeProvider';

const schema = z.object({
  linkOrTitle: z.string().min(3, 'Podaj link lub tytuł'),
  price: z.string().min(1, 'Podaj cenę'),
  category: z.enum(['ELECTRONICS', 'CAR', 'FASHION']),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function AnalyzeScreen() {
  const router = useRouter();
  const { colors, spacing, typography } = useTheme();
  const [jobId, setJobId] = useState<string | null>(null);
  const [stage, setStage] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const { control, handleSubmit, formState: { errors } } = useForm<FormValues>({
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
    const timer = setInterval(async () => {
      const job = await api.analyze.pollJob(jobId);
      if (job.status === 'done') {
        setStage('done');
        setMessage('Analiza zakończona.');
        if (job.result?.snapshot_id) {
          router.push({
            pathname: '/offer/[id]',
            params: { id: String(job.result.snapshot_id) },
          });
        }
        clearInterval(timer);
      } else if (job.status === 'error') {
        setStage('error');
        setMessage('Analiza nie powiodła się.');
        clearInterval(timer);
      }
    }, 800);
    return () => clearInterval(timer);
  }, [jobId, stage, router]);

  const onSubmit = handleSubmit(async (values) => {
    setStage('running');
    setMessage('Trwa analiza — możesz opuścić ekran i wrócić później.');
    try {
      const response = await api.analyze.submitManual({
        external_id: values.linkOrTitle.slice(0, 120),
        title: values.linkOrTitle.slice(0, 500),
        price: values.price,
        category: values.category,
        description: values.description,
      });
      if ('job_id' in response) {
        setJobId(response.job_id);
        return;
      }
      setStage('done');
      setMessage('Analiza zakończona (odpowiedź synchroniczna).');
    } catch (error) {
      setStage('error');
      setMessage(apiErrorMessage(error));
    }
  });

  return (
    <AppScreen scroll>
      <Header title="Analizuj" />
      <DemoBanner />
      <Text style={[typography.body, { color: colors.textMuted, marginBottom: spacing.lg }]}>
        Przekaż link, opis lub specyfikację zgodnie z API. Skanery nie działają na telefonie.
      </Text>

      <Controller
        control={control}
        name="linkOrTitle"
        render={({ field: { onChange, value } }) => (
          <FormField
            label="Link lub tytuł ogłoszenia"
            value={value}
            onChangeText={onChange}
            error={errors.linkOrTitle?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="price"
        render={({ field: { onChange, value } }) => (
          <FormField
            label="Cena (zł)"
            keyboardType="decimal-pad"
            value={value}
            onChangeText={onChange}
            error={errors.price?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="description"
        render={({ field: { onChange, value } }) => (
          <FormField
            label="Opis / specyfikacja (opcjonalnie)"
            multiline
            numberOfLines={4}
            value={value}
            onChangeText={onChange}
            style={{ minHeight: 96, textAlignVertical: 'top' }}
          />
        )}
      />

      <PrimaryButton
        label={stage === 'running' ? 'Analiza w toku…' : 'Wyślij do analizy'}
        onPress={onSubmit}
        loading={stage === 'running'}
      />

      {message ? (
        <View style={{ marginTop: spacing.lg }}>
          <Text style={[typography.body, { color: colors.text }]}>{message}</Text>
        </View>
      ) : null}
    </AppScreen>
  );
}
