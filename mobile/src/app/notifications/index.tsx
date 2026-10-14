import React from 'react';
import { FlatList, Text, View } from 'react-native';

import { api } from '@/api';
import { AppScreen } from '@/components/AppScreen';
import { DemoBanner } from '@/components/DemoBanner';
import { EmptyState } from '@/components/EmptyState';
import { Header } from '@/components/Header';
import { useTheme } from '@/theme/ThemeProvider';
import { formatUserDateTime } from '@/utils/datetime';

export default function NotificationsScreen() {
  const { colors, spacing, typography, radii } = useTheme();
  const items = api.notifications();

  return (
    <AppScreen padded={false}>
      <View style={{ paddingHorizontal: spacing.lg }}>
        <Header title="Powiadomienia" showBack showNotifications={false} />
        <DemoBanner />
        {api.mode === 'live' ? (
          <Text style={[typography.caption, { color: colors.textMuted, marginBottom: spacing.sm }]}>
            Skrzynka zdarzeń live wymaga endpointu notifications — patrz FRONTEND_BACKEND_GAPS.md.
          </Text>
        ) : null}
      </View>

      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}
        ListEmptyComponent={
          <EmptyState title="Brak powiadomień" description="Alerty pojawią się tutaj." />
        }
        renderItem={({ item }) => (
          <View
            style={{
              backgroundColor: colors.surface,
              borderRadius: radii.md,
              padding: spacing.md,
              borderWidth: 1,
              borderColor: colors.border,
              opacity: item.read ? 0.75 : 1,
            }}
          >
            <Text style={[typography.caption, { color: colors.accent }]}>{item.category}</Text>
            <Text style={[typography.bodyStrong, { color: colors.text }]}>{item.title}</Text>
            <Text style={[typography.body, { color: colors.textMuted }]}>{item.reason}</Text>
            <Text style={[typography.caption, { color: colors.textMuted }]}>
              {formatUserDateTime(item.at)}
            </Text>
          </View>
        )}
      />
    </AppScreen>
  );
}
