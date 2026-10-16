import React from 'react';

import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { RadarItem } from './legacyApiClient';

export type PlatformFilter =
  'ALL' | 'OLX' | 'FACEBOOK';

export type DecisionFilter =
  'ALL' | 'HOT' | 'BUY' | 'WATCH'
  | 'SKIP' | 'REVIEW' | 'UNKNOWN';

export function priceLimit(
  value: string,
): number | null {
  if (!value.trim()) return null;

  const input = value.trim().replace(',', '.');

  if (!/^\d{1,7}(\.\d{1,2})?$/.test(input)) {
    return null;
  }

  const limit = Math.round(
    Number(input) * 100,
  );

  return Number.isSafeInteger(limit)
    ? limit
    : null;
}

export function matchRadar(
  item: RadarItem,
  decision: DecisionFilter,
  platform: PlatformFilter,
  limit: number | null,
): boolean {
  if (
    decision !== 'ALL' &&
    item.decision.toUpperCase() !== decision
  ) {
    return false;
  }

  const source = item.platform.toUpperCase();

  if (
    platform === 'FACEBOOK' &&
    !source.includes('FACEBOOK') &&
    source !== 'FB'
  ) {
    return false;
  }

  if (
    platform === 'OLX' &&
    !source.includes('OLX')
  ) {
    return false;
  }

  if (
    limit !== null &&
    (
      item.price_minor === null ||
      item.price_minor > limit
    )
  ) {
    return false;
  }

  return true;
}

type Props = {
  items: RadarItem[];
  visibleCount: number;

  query: string;
  onQuery: (value: string) => void;

  decision: DecisionFilter;
  onDecision: (value: DecisionFilter) => void;

  platform: PlatformFilter;
  onPlatform: (value: PlatformFilter) => void;

  maxPrice: string;
  onMaxPrice: (value: string) => void;
};

export default function RadarPanel(
  props: Props,
) {
  const stats = {
    hot: props.items.filter(
      x => x.decision === 'HOT',
    ).length,

    buy: props.items.filter(
      x => x.decision === 'BUY',
    ).length,

    watch: props.items.filter(
      x => x.decision === 'WATCH',
    ).length,
  };

  const invalidPrice =
    props.maxPrice.trim() !== '' &&
    priceLimit(props.maxPrice) === null;

  return (
    <View style={s.wrapper}>
      <Text style={s.note}>
        Dashboard — tylko wczytane oferty
      </Text>

      <View style={s.stats}>
        <Text style={s.stat}>
          Wczytane: {props.items.length}
        </Text>

        <Text style={s.stat}>
          HOT: {stats.hot}
        </Text>

        <Text style={s.stat}>
          BUY: {stats.buy}
        </Text>

        <Text style={s.stat}>
          WATCH: {stats.watch}
        </Text>
      </View>

      <TextInput
        style={s.input}
        placeholder="Szukaj CPU, GPU lub nazwy..."
        placeholderTextColor="#96a0b0"
        value={props.query}
        onChangeText={props.onQuery}
        maxLength={120}
        autoCorrect={false}
        autoCapitalize="none"
        returnKeyType="search"
      />

      <Text style={s.note}>
        Szukaj po tytule we wszystkich
        zapisanych ofertach
      </Text>

      <View style={s.chips}>
        {(
          [
            'ALL',
            'OLX',
            'FACEBOOK',
          ] as PlatformFilter[]
        ).map(value => (
          <Pressable
            key={value}
            onPress={() => props.onPlatform(value)}
            style={[
              s.chip,
              props.platform === value && s.active,
            ]}
          >
            <Text style={s.chipText}>
              {value === 'ALL'
                ? 'Wszystkie źródła'
                : value}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={s.chips}>
        {(
          [
            'ALL',
            'HOT',
            'BUY',
            'WATCH',
            'SKIP',
            'REVIEW',
            'UNKNOWN',
          ] as DecisionFilter[]
        ).map(value => (
          <Pressable
            key={value}
            onPress={() => props.onDecision(value)}
            style={[
              s.chip,
              props.decision === value && s.active,
            ]}
          >
            <Text style={s.chipText}>
              {value}
            </Text>
          </Pressable>
        ))}
      </View>

      <TextInput
        style={s.input}
        placeholder="Maks. cena zakupu (zł)"
        placeholderTextColor="#96a0b0"
        keyboardType="decimal-pad"
        value={props.maxPrice}
        onChangeText={props.onMaxPrice}
        maxLength={12}
      />

      {invalidPrice && (
        <Text style={s.error}>
          Niepoprawna maksymalna cena.
        </Text>
      )}

      <Text style={s.note}>
        Po filtrach: {props.visibleCount}.
        Filtry ceny, źródła i decyzji obejmują
        tylko wczytane strony.
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  wrapper: {
    gap: 9,
    marginBottom: 14,
  },
  stats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  stat: {
    backgroundColor: '#253143',
    color: '#e8f0ff',
    padding: 9,
    borderRadius: 8,
    fontSize: 12,
  },
  note: {
    color: '#9da8bd',
    fontSize: 12,
  },
  input: {
    color: '#fff',
    backgroundColor: '#1d2430',
    borderColor: '#454c5e',
    borderWidth: 1,
    padding: 12,
    borderRadius: 10,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    borderWidth: 1,
    borderColor: '#454c5e',
    borderRadius: 8,
    paddingHorizontal: 9,
    paddingVertical: 8,
  },
  active: {
    backgroundColor: '#4169e1',
  },
  chipText: {
    color: '#fff',
    fontSize: 12,
  },
  error: {
    color: '#ff8585',
    fontSize: 12,
  },
});
