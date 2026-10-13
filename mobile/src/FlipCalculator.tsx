import React, { useState } from 'react';

import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import {
  FlipPreviewResult,
  previewFlip,
} from './api';

function parsePLN(value: string): number | null {
  const normalized = value
    .trim()
    .replace(/\s/g, '')
    .replace(',', '.');

  if (!/^\d{1,7}(\.\d{1,2})?$/.test(normalized)) {
    return null;
  }

  const [whole, fractional = ''] = normalized.split('.');

  const minor =
    Number(whole) * 100 +
    Number(fractional.padEnd(2, '0'));

  return Number.isSafeInteger(minor) ? minor : null;
}

function pln(minor: number): string {
  return (minor / 100).toLocaleString('pl-PL', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + ' zł';
}

type Props = {
  initialPurchaseMinor?: number | null;
  initialSaleMinor?: number | null;
  onBack: () => void;
};

function initialMoney(
  value: number | null | undefined,
  fallback: string,
): string {
  return (
    typeof value === 'number' &&
    Number.isSafeInteger(value) &&
    value > 0
  )
    ? (value / 100).toFixed(2)
    : fallback;
}

export default function FlipCalculator({
  initialPurchaseMinor,
  initialSaleMinor,
  onBack,
}: Props) {
  const [purchase, setPurchase] = useState(
    initialMoney(initialPurchaseMinor, '1500'),
  );

  const [sale, setSale] = useState(
    initialMoney(initialSaleMinor, '2200'),
  );

  const [transport, setTransport] = useState('0');
  const [repair, setRepair] = useState('100');
  const [fees, setFees] = useState('0');
  const [other, setOther] = useState('0');

  const [result, setResult] =
    useState<FlipPreviewResult | null>(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  function field(
    label: string,
    value: string,
    change: (v: string) => void,
  ) {
    return (
      <View style={styles.field}>
        <Text style={styles.label}>{label}</Text>

        <TextInput
          value={value}
          onChangeText={(v) => {
            change(v);
            setResult(null);
            setError('');
          }}
          keyboardType="decimal-pad"
          placeholder="0,00"
          placeholderTextColor="#8793a7"
          style={styles.input}
          maxLength={14}
        />
      </View>
    );
  }

  async function calculate() {
    if (busy) return;

    const parsed = [
      purchase,
      sale,
      transport,
      repair,
      fees,
      other,
    ].map(parsePLN);

    if (parsed.some((v) => v === null)) {
      setError('Wprowadź poprawne kwoty w PLN.');
      return;
    }

    const [
      buy,
      sell,
      shipping,
      service,
      fee,
      miscellaneous,
    ] = parsed as number[];

    if (buy <= 0 || sell <= 0) {
      setError(
        'Cena zakupu i sprzedaży muszą być większe od zera.',
      );
      return;
    }

    setBusy(true);
    setError('');
    setResult(null);

    try {
      const data = await previewFlip({
        purchase_minor: buy,
        sale_minor: sell,
        costs: {
          TRANSPORT_BUY: shipping,
          REPAIR: service,
          FEE: fee,
          OTHER: miscellaneous,
        },
        confidence: 'LOW',
        condition: 'unknown',
      });

      setResult(data);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : String(e),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView
      keyboardShouldPersistTaps="handled"
      contentContainerStyle={styles.content}
    >
      <Pressable
        onPress={onBack}
        style={styles.back}
      >
        <Text style={styles.backText}>
          ← Wróć do radaru
        </Text>
      </Pressable>

      <Text style={styles.heading}>
        Kalkulator flipa
      </Text>

      <Text style={styles.muted}>
        Obliczenia wykonuje backend Flip Hunter.
      </Text>

      {field('Cena zakupu', purchase, setPurchase)}
      {field('Przewidywana cena sprzedaży', sale, setSale)}
      {field('Transport', transport, setTransport)}
      {field('Naprawa i części', repair, setRepair)}
      {field('Prowizje', fees, setFees)}
      {field('Inne koszty', other, setOther)}

      <Pressable
        onPress={calculate}
        disabled={busy}
        style={styles.button}
      >
        <Text style={styles.buttonText}>
          Oblicz opłacalność
        </Text>
      </Pressable>

      {busy && <ActivityIndicator />}

      {!!error && (
        <Text style={styles.error}>
          {error}
        </Text>
      )}

      {result && (
        <View style={styles.result}>
          <Text style={styles.resultHeading}>
            Wynik analizy
          </Text>

          <Text style={styles.muted}>
            Zysk operacyjny
          </Text>

          <Text
            style={[
              styles.profit,
              result.operating_profit_minor < 0 &&
                styles.loss,
            ]}
          >
            {pln(result.operating_profit_minor)}
          </Text>

          <Text style={styles.detail}>
            ROI: {(result.roi_bps / 100).toFixed(2)}%
          </Text>

          <Text style={styles.detail}>
            Łączny koszt: {
              pln(result.total_investment_minor)
            }
          </Text>

          <Text style={styles.detail}>
            Maksymalna cena zakupu: {
              pln(result.max_purchase_minor)
            }
          </Text>

          <Text style={styles.detail}>
            Ocena: {result.decision}
          </Text>

          <Text style={styles.note}>
            REVIEW oznacza brak potwierdzonej
            pewności wyceny. Kalkulacja opiera się
            na podanej cenie sprzedaży i nie
            uwzględnia podatków.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: 48,
    gap: 12,
  },
  back: {
    paddingVertical: 8,
  },
  backText: {
    color: '#99b6ff',
  },
  heading: {
    color: '#fff',
    fontSize: 23,
    fontWeight: '700',
  },
  muted: {
    color: '#a5b0c1',
    fontSize: 13,
  },
  field: {
    gap: 5,
  },
  label: {
    color: '#a5b0c1',
    fontSize: 13,
  },
  input: {
    backgroundColor: '#1d2430',
    color: '#fff',
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#3b4251',
    fontSize: 17,
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
  result: {
    backgroundColor: '#1d2430',
    padding: 18,
    borderRadius: 12,
    gap: 9,
  },
  resultHeading: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  profit: {
    color: '#7bd9b1',
    fontSize: 30,
    fontWeight: '700',
  },
  loss: {
    color: '#ff8585',
  },
  detail: {
    color: '#fff',
  },
  note: {
    color: '#a5b0c1',
    fontSize: 12,
    lineHeight: 18,
  },
  error: {
    color: '#ff8585',
  },
});
