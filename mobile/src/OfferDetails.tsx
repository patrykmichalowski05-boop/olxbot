import React from 'react';

import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { RadarItem } from './api';

type Props = {
  item: RadarItem;
  onBack: () => void;
  onOpen: (url: string | null) => void;
  onCalculate: () => void;
};

function money(value: number | null): string {
  return value === null
    ? 'Brak ceny'
    : (value / 100).toFixed(2) + ' zł';
}

export default function OfferDetails({
  item,
  onBack,
  onOpen,
  onCalculate,
}: Props) {
  const valuation = item.valuation || {};

  const summary = Object.entries(valuation)
    .filter(([key, value]) =>
      [
        'quick_sale',
        'profit',
        'confidence',
        'valuation_source',
        'total_cost',
      ].includes(key) &&
      (
        typeof value === 'string' ||
        typeof value === 'number'
      ),
    );

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Pressable
        onPress={onBack}
        style={styles.back}
      >
        <Text style={styles.link}>
          ← Wróć do radaru
        </Text>
      </Pressable>

      <Text style={styles.platform}>
        {item.platform} · {item.decision}
      </Text>

      <Text style={styles.title}>
        {item.title || 'Oferta bez tytułu'}
      </Text>

      <Text style={styles.price}>
        {money(item.price_minor)}
      </Text>

      <Text style={styles.meta}>
        Ostatni zapis: {
          item.observed_at || 'brak daty'
        }
      </Text>

      <View style={styles.panel}>
        <Text style={styles.subtitle}>
          Dostępna wycena
        </Text>

        {summary.length ? (
          summary.map(([key, value]) => (
            <Text key={key} style={styles.row}>
              {key}: {String(value)}
            </Text>
          ))
        ) : (
          <Text style={styles.meta}>
            Brak pełnej wyceny w zapisanej ofercie.
          </Text>
        )}
      </View>

      <Pressable
        onPress={onCalculate}
        style={styles.button}
      >
        <Text style={styles.buttonText}>
          Policz opłacalność
        </Text>
      </Pressable>

      {!!item.url && (
        <Pressable
          onPress={() => onOpen(item.url)}
          style={styles.secondary}
        >
          <Text style={styles.link}>
            Otwórz oryginalną ofertę ↗
          </Text>
        </Pressable>
      )}

      <Text style={styles.meta}>
        Dane historyczne. Cena i dostępność
        mogą się zmienić.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: 14,
    paddingBottom: 50,
  },
  back: {
    paddingVertical: 8,
  },
  link: {
    color: '#99b6ff',
  },
  platform: {
    color: '#9da8bd',
    fontSize: 13,
  },
  title: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '700',
  },
  price: {
    color: '#7bd9b1',
    fontSize: 24,
    fontWeight: '700',
  },
  meta: {
    color: '#a5b0c1',
    fontSize: 12,
  },
  panel: {
    backgroundColor: '#1d2430',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  subtitle: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '700',
  },
  row: {
    color: '#e8ebf2',
  },
  button: {
    backgroundColor: '#4169e1',
    padding: 15,
    borderRadius: 10,
  },
  buttonText: {
    color: '#fff',
    textAlign: 'center',
    fontWeight: '700',
  },
  secondary: {
    paddingVertical: 10,
  },
});
