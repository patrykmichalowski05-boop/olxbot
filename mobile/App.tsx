import FlipCalculator from './src/FlipCalculator';
import OfferDetails from './src/OfferDetails';

import React, {
  useEffect,
  useState,
} from 'react';

import {
  ActivityIndicator,
  Alert,
  FlatList,
  Linking,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import {
  clearSession,
  getRadar,
  getRadarPage,
  hasSession,
  RadarItem,
  login,
} from './src/api';

export default function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authorized, setAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<RadarItem[]>([]);
  const [nextCursor, setNextCursor] =
    useState<number | null>(null);
  const [filter, setFilter] = useState('ALL');
  const [screen, setScreen] = useState<'radar' | 'calculator' | 'details'>('radar');
  const [selected, setSelected] = useState<RadarItem | null>(null);
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');

    try {
      const first = await getRadar();
      setItems(first);
      setNextCursor(
        first.length === 50
          ? first[first.length - 1].snapshot_id
          : null
      );
    } catch (e) {
      setError(
        e instanceof Error ? e.message : String(e)
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    hasSession().then(async (yes) => {
      setAuthorized(yes);

      if (yes) {
        await refresh();
      } else {
        setLoading(false);
      }
    }).catch(() => setLoading(false));
  }, []);

  async function submit() {
    setLoading(true);
    setError('');

    try {
      await login(username, password);
      setAuthorized(true);
      await refresh();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : String(e)
      );
      setLoading(false);
    }
  }

  async function loadMore() {
    if (loading || nextCursor === null) return;

    setLoading(true);

    try {
      const page = await getRadarPage(nextCursor);

      setItems((current) => {
        const known = new Set(
          current.map((item) => item.snapshot_id)
        );

        return [
          ...current,
          ...page.items.filter(
            (item) => !known.has(item.snapshot_id)
          ),
        ];
      });

      setNextCursor(page.next_before_id);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : String(e)
      );
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    await clearSession();
    setAuthorized(false);
    setItems([]);
    setSelected(null);
    setScreen('radar');
    setPassword('');
  }

  function openOriginal(url: string | null) {
    if (!url) return;

    const valid =
      /^https:\/\/([a-z0-9-]+\.)*(olx\.pl|facebook\.com)\//i
        .test(url);

    if (!valid) {
      Alert.alert('Nieznany adres oferty');
      return;
    }

    Linking.openURL(url).catch(() => {
      Alert.alert('Nie mozna otworzyc linku');
    });
  }

  const visibleItems = items.filter(
    (item) =>
      filter === 'ALL' || item.decision === filter
  );

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.heading}>Flip Hunter</Text>

      {!authorized ? (
        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Uzytkownik"
            placeholderTextColor="#888"
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
          />

          <TextInput
            style={styles.input}
            placeholder="Haslo"
            placeholderTextColor="#888"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          <Pressable
            style={styles.button}
            onPress={submit}
            disabled={loading}
          >
            <Text style={styles.action}>
              Zaloguj
            </Text>
          </Pressable>
        </View>
      ) : (
        <>
          <View style={styles.toolbar}>
            <Pressable onPress={refresh}>
              <Text style={styles.link}>
                Odswiez radar
              </Text>
            </Pressable>

            <Pressable onPress={logout}>
              <Text style={styles.link}>
                Wyloguj
              </Text>
            </Pressable>
          </View>

          <View style={styles.navigation}>
            <Pressable
              onPress={() => {
                setScreen('radar');
                setSelected(null);
              }}
              style={styles.navButton}
            >
              <Text style={styles.link}>Radar</Text>
            </Pressable>

            <Pressable
              onPress={() => {
                setSelected(null);
                setScreen('calculator');
              }}
              style={styles.navButton}
            >
              <Text style={styles.link}>Kalkulator</Text>
            </Pressable>
          </View>

          {screen === 'calculator' ? (
            <FlipCalculator
              initialPurchaseMinor={selected?.price_minor}
              initialSaleMinor={
                typeof selected?.valuation?.quick_sale === 'number'
                  && Number.isFinite(selected.valuation.quick_sale)
                  && selected.valuation.quick_sale > 0
                  ? Math.round(selected.valuation.quick_sale * 100)
                  : null
              }
              onBack={() => {
                setSelected(null);
                setScreen('radar');
              }}
            />
          ) : screen === 'details' && selected ? (
            <OfferDetails
              item={selected}
              onBack={() => {
                setSelected(null);
                setScreen('radar');
              }}
              onOpen={openOriginal}
              onCalculate={() => setScreen('calculator')}
            />
          ) : (
            <>
          <View style={styles.filters}>
            {['ALL', 'HOT', 'BUY', 'WATCH', 'SKIP'].map(
              (value) => (
                <Pressable
                  key={value}
                  onPress={() => setFilter(value)}
                  style={[
                    styles.filterButton,
                    filter === value && styles.filterActive,
                  ]}
                >
                  <Text style={styles.filterText}>
                    {value}
                  </Text>
                </Pressable>
              )
            )}
          </View>

          <FlatList
            data={visibleItems}
            keyExtractor={(item) => String(item.snapshot_id)}
            renderItem={({ item }) => (
              <Pressable
                style={styles.card}
                onPress={() => {
                  setSelected(item);
                  setScreen('details');
                }}
              >
                <Text style={styles.platform}>
                  {item.platform} · {item.decision}
                </Text>

                <Text style={styles.title}>
                  {item.title || 'Oferta bez tytulu'}
                </Text>

                <Text style={styles.price}>
                  {item.price_minor === null
                    ? 'Cena nieznana'
                    : `${(item.price_minor / 100).toFixed(2)} zl`}
                </Text>
              </Pressable>
            )}
            ListFooterComponent={
              nextCursor !== null ? (
                <Pressable
                  onPress={loadMore}
                  disabled={loading}
                  style={styles.button}
                >
                  <Text style={styles.action}>
                    Wczytaj kolejne oferty
                  </Text>
                </Pressable>
              ) : null
            }
            ListEmptyComponent={
              !loading
                ? <Text style={styles.muted}>Brak ofert</Text>
                : null
            }
          />
            </>
          )}
        </>
      )}

      {loading && <ActivityIndicator />}

      {!!error && (
        <Text style={styles.error}>{error}</Text>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#10141c',
    padding: 18,
  },
  heading: {
    color: '#f2f4fa',
    fontSize: 27,
    fontWeight: '700',
    marginBottom: 22,
  },
  form: {
    gap: 12,
  },
  input: {
    color: 'white',
    borderColor: '#3b4251',
    borderWidth: 1,
    borderRadius: 10,
    padding: 13,
  },
  button: {
    backgroundColor: '#4169e1',
    padding: 14,
    borderRadius: 10,
  },
  action: {
    color: 'white',
    textAlign: 'center',
    fontWeight: '700',
  },
  toolbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 18,
  },
  link: {
    color: '#99b6ff',
  },
  card: {
    backgroundColor: '#1d2430',
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
  },
  platform: {
    color: '#9da8bd',
    fontSize: 12,
  },
  title: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginVertical: 7,
  },
  price: {
    color: '#7bd9b1',
    fontSize: 18,
    fontWeight: '700',
  },
  navigation: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  navButton: {
    backgroundColor: '#1d2430',
    padding: 12,
    borderRadius: 10,
  },
  filters: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 12,
  },
  filterButton: {
    borderWidth: 1,
    borderColor: '#454c5e',
    borderRadius: 8,
    paddingHorizontal: 9,
    paddingVertical: 7,
  },
  filterActive: {
    backgroundColor: '#4169e1',
  },
  filterText: {
    color: '#ffffff',
    fontSize: 12,
  },
  muted: {
    color: '#a5acb8',
  },
  error: {
    color: '#ff8585',
    marginTop: 12,
  },
});
