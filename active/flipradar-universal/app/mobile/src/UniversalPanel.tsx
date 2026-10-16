import React, {
  useEffect,
  useState,
} from 'react';

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
  addUniversalWatch,
  analyzeUniversalManual,
  closeUniversalWatch,
  getUniversalWatchlist,
  UniversalWatchItem,
} from './legacyApiClient';

type Category = 'ELECTRONICS' | 'CAR' | 'FASHION';

export default function UniversalPanel() {
  const [items, setItems] =
    useState<UniversalWatchItem[]>([]);

  const [key, setKey] = useState('');
  const [title, setTitle] = useState('');
  const [price, setPrice] = useState('');
  const [category, setCategory] =
    useState<Category>('ELECTRONICS');

  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  async function reload() {
    const rows = await getUniversalWatchlist();
    setItems(rows);
  }

  useEffect(() => {
    void reload().catch(e =>
      setMessage(String(e)),
    );
  }, []);

  async function addWatch() {
    setBusy(true);
    setMessage('');

    try {
      await addUniversalWatch(
        key.trim(),
        title.trim(),
      );

      await reload();

      setMessage('Dodano do watchlisty.');
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function closeWatch(k: string) {
    setBusy(true);

    try {
      await closeUniversalWatch(k);
      await reload();
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function analyze() {
    setBusy(true);
    setMessage('');

    try {
      const result = await analyzeUniversalManual({
        external_id: key.trim(),
        title: title.trim(),
        price: price.trim(),
        category,
      });

      setMessage(
        'Wynik: ' + result.decision
      );
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={s.page}>
      <Text style={s.header}>
        Universal — tryb testowy
      </Text>

      <Text style={s.note}>
        Analiza reczna nie potwierdza automatycznie
        ceny odsprzedazy ani okazji.
      </Text>

      <TextInput
        style={s.input}
        value={key}
        onChangeText={setKey}
        placeholder="ID oferty"
        placeholderTextColor="#8d99ab"
        maxLength={120}
      />

      <TextInput
        style={s.input}
        value={title}
        onChangeText={setTitle}
        placeholder="Nazwa przedmiotu"
        placeholderTextColor="#8d99ab"
        maxLength={500}
      />

      <TextInput
        style={s.input}
        value={price}
        onChangeText={setPrice}
        placeholder="Cena zakupu w zł"
        placeholderTextColor="#8d99ab"
        keyboardType="decimal-pad"
      />

      <View style={s.categories}>
        {(['ELECTRONICS','CAR','FASHION'] as Category[])
          .map(value => (
            <Pressable
              key={value}
              onPress={() => setCategory(value)}
            >
              <Text style={
                category === value
                  ? s.selected
                  : s.link
              }>
                {value}
              </Text>
            </Pressable>
          ))}
      </View>

      <Pressable
        style={s.button}
        disabled={busy}
        onPress={() => void analyze()}
      >
        <Text style={s.buttonText}>
          Analizuj recznie
        </Text>
      </Pressable>

      <Pressable
        style={s.button}
        disabled={busy}
        onPress={() => void addWatch()}
      >
        <Text style={s.buttonText}>
          Dodaj do watchlisty
        </Text>
      </Pressable>

      {!!message && (
        <Text style={s.note}>{message}</Text>
      )}

      {busy && <ActivityIndicator />}

      <Text style={s.header}>Watchlista</Text>

      {items.map(item => (
        <View
          key={item.listing_key}
          style={s.card}
        >
          <Text style={s.white}>
            {item.label}
          </Text>

          <Text style={s.note}>
            {item.listing_key}
          </Text>

          <Pressable
            disabled={busy}
            onPress={() =>
              void closeWatch(item.listing_key)
            }
          >
            <Text style={s.link}>
              Zamknij obserwacje
            </Text>
          </Pressable>
        </View>
      ))}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  page: {
    gap: 13,
    paddingBottom: 40,
  },
  header: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
  },
  note: {
    color: '#a5b0c1',
    fontSize: 13,
  },
  input: {
    color: '#fff',
    borderColor: '#414b5c',
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
  },
  categories: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  link: {
    color: '#9bbcff',
  },
  selected: {
    color: '#7bd9b1',
    fontWeight: '700',
  },
  button: {
    backgroundColor: '#4169e1',
    padding: 14,
    borderRadius: 10,
  },
  buttonText: {
    color: '#fff',
    textAlign: 'center',
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#1d2430',
    borderRadius: 10,
    padding: 13,
    gap: 7,
  },
  white: {
    color: '#fff',
  },
});
