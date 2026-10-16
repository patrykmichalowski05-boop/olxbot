import React, { useState } from 'react';
import { Platform, Text, View } from 'react-native';
import PortalPage from '@/features/portal/PortalPage';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { FormField } from '@/components/FormField';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useAuth } from '@/features/auth/AuthContext';
import { useTheme } from '@/theme/ThemeProvider';
import { apiErrorMessage } from '@/api/errors';

const schema = z.object({
  username: z.string().min(1, 'Podaj login'),
  password: z.string().min(1, 'Podaj hasło'),
});

type FormValues = z.infer<typeof schema>;

export default function LoginScreen() {
  return Platform.OS === 'web' ? <PortalPage page="login" /> : <LegacyLoginScreen />;
}

function LegacyLoginScreen() {
  const { login, checkConnection, mode, ready } = useAuth();
  const { colors, spacing, typography } = useTheme();
  const [apiMessage, setApiMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { username: '', password: '' },
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true);
    setApiMessage('');
    try {
      await login(values.username, values.password);
    } catch (error) {
      setError('password', { message: apiErrorMessage(error) });
    } finally {
      setSubmitting(false);
    }
  });

  if (!ready) {
    return null;
  }

  return (
    <AppScreen scroll>
      <DemoBanner />
      <Text style={[typography.title, { color: colors.text, marginBottom: spacing.xs }]}>
        FlipRadar
      </Text>
      <Text style={[typography.body, { color: colors.textMuted, marginBottom: spacing.xl }]}>
        {mode === 'demo'
          ? 'Podgląd interfejsu z danymi demonstracyjnymi.'
          : 'Zaloguj się i zarządzaj swoimi okazjami.'}
      </Text>

      <Controller
        control={control}
        name="username"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Login"
            autoCapitalize="none"
            autoCorrect={false}
            onBlur={onBlur}
            onChangeText={onChange}
            value={value}
            error={errors.username?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="password"
        render={({ field: { onChange, onBlur, value } }) => (
          <FormField
            label="Hasło"
            secureTextEntry
            onBlur={onBlur}
            onChangeText={onChange}
            value={value}
            error={errors.password?.message}
          />
        )}
      />

      <PrimaryButton label="Zaloguj" onPress={onSubmit} loading={submitting} />

      {mode === 'live' ? (
        <View style={{ marginTop: spacing.lg }}>
          <PrimaryButton
            label="Sprawdź połączenie"
            variant="secondary"
            onPress={async () => {
              try {
                await checkConnection();
                setApiMessage('Usługa jest dostępna.');
              } catch (error) {
                setApiMessage(apiErrorMessage(error));
              }
            }}
          />
          {apiMessage ? (
            <Text style={[typography.caption, { color: colors.textMuted, marginTop: spacing.sm }]}>
              {apiMessage}
            </Text>
          ) : null}
        </View>
      ) : null}
    </AppScreen>
  );
}
