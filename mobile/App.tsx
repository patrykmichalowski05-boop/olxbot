import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  ActivityIndicator,
  Alert,
  FlatList,
  Linking,
  Pressable,
  RefreshControl,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import FlipCalculator from './src/FlipCalculator';
import OfferDetails from './src/OfferDetails';

import RadarPanel, {
  DecisionFilter,
  PlatformFilter,
  matchRadar,
  priceLimit,
} from './src/RadarPanel';

import {
  checkApiConnection,
  clearSession,
  getRadarPage,
  hasSession,
  login,
  RadarItem,
} from './src/api';

type Screen =
  'radar' | 'calculator' | 'details';

export default function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [authorized, setAuthorized] =
    useState(false);

  const [loading, setLoading] =
    useState(true);

  const [items, setItems] =
    useState<RadarItem[]>([]);

  const [nextCursor, setNextCursor] =
    useState<number | null>(null);

  const [decision, setDecision] =
    useState<DecisionFilter>('ALL');

  const [platform, setPlatform] =
    useState<PlatformFilter>('ALL');

  const [query, setQuery] = useState('');
  const [maxPrice, setMaxPrice] = useState('');

  const [screen, setScreen] =
    useState<Screen>('radar');

  const [selected, setSelected] =
    useState<RadarItem | null>(null);

  const [error, setError] = useState('');

  const [connectionStatus, setConnectionStatus] =
    useState('');

  const [checkingConnection, setCheckingConnection] =
    useState(false);

  const version = useRef(0);
  const loadedQuery = useRef('');

  async function loadFirst(
    search: string,
    requestId: number,
  ) {
    if (version.current !== requestId) {
      return;
    }

    setLoading(true);
    setError('');

    loadedQuery.current = search;

    try {
      const page = await getRadarPage(
        null,
        search,
      );

      if (version.current !== requestId) {
        return;
      }

      setItems(page.items);
      setNextCursor(page.next_before_id);
    } catch (e) {
      if (version.current === requestId) {
        setError(
          e instanceof Error
            ? e.message
            : String(e),
        );
      }
    } finally {
      if (version.current === requestId) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    let alive = true;

    hasSession()
      .then(yes => {
        if (alive) {
          setAuthorized(yes);
        }
      })
      .catch(e => {
        if (alive) {
          setError(String(e));
        }
      })
      .finally(() => {
        if (alive) {
          setLoading(false);
        }
      });

    return () => {
      alive = false;
      version.current += 1;
    };
  }, []);

  useEffect(() => {
    if (!authorized) {
      return;
    }

    const requestId = ++version.current;

    setItems([]);
    setNextCursor(null);
    setLoading(true);

    const handle = setTimeout(() => {
      void loadFirst(
        query.trim(),
        requestId,
      );
    }, 350);

    return () => clearTimeout(handle);
  }, [authorized, query]);

  async function diagnoseConnection() {
    if (checkingConnection) return;

    setCheckingConnection(true);
    setConnectionStatus('Sprawdzanie API...');

    try {
      const result = await checkApiConnection();
      setConnectionStatus(result);
    } catch (e) {
      setConnectionStatus(
        e instanceof Error
          ? e.message
          : String(e),
      );
    } finally {
      setCheckingConnection(false);
    }
  }

  async function submit() {
    setLoading(true);
    setError('');

    try {
      await login(username, password);
      setAuthorized(true);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : String(e),
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadMore() {
    if (loading || nextCursor === null) {
      return;
    }

    const requestId = version.current;

    setLoading(true);

    try {
      const page = await getRadarPage(
        nextCursor,
        loadedQuery.current,
      );

      if (requestId !== version.current) {
        return;
      }

      setItems(old => {
        const known = new Set(
          old.map(item => item.snapshot_id),
        );

        return [
          ...old,
          ...page.items.filter(
            item => !known.has(item.snapshot_id),
          ),
        ];
      });

      setNextCursor(page.next_before_id);
    } catch (e) {
      if (requestId === version.current) {
        setError(
          e instanceof Error
            ? e.message
            : String(e),
        );
      }
    } finally {
      if (requestId === version.current) {
        setLoading(false);
      }
    }
  }

  async function logout() {
    version.current += 1;
    setLoading(true);

    try {
      await clearSession();
    } finally {
      setAuthorized(false);
      setItems([]);
      setNextCursor(null);
      setSelected(null);
      setScreen('radar');
      setPassword('');
      setLoading(false);
    }
  }

  function openOriginal(
    url: string | null,
  ) {
    if (!url) return;

    const valid =
      /^https:\/\/(?:[a-z0-9-]+\.)*(?:olx\.pl|facebook\.com)\//i
        .test(url);

    if (!valid) {
      Alert.alert('Nieznany adres oferty');
      return;
    }

    Linking.openURL(url).catch(() => {
      Alert.alert(
        'Nie można otworzyć linku',
      );
    });
  }

  const limit = priceLimit(maxPrice);

  const invalidPrice =
    maxPrice.trim() !== '' &&
    limit === null;

  const visible = invalidPrice
    ? []
    : items.filter(
        item => matchRadar(
          item,
          decision,
          platform,
          limit,
        ),
      );

  const estimatedSaleMinor =
    typeof selected?.valuation?.quick_sale ===
      'number' &&
    Number.isFinite(
      selected.valuation.quick_sale,
    ) &&
    selected.valuation.quick_sale > 0
      ? Math.round(
          selected.valuation.quick_sale * 100,
        )
      : null;

  return (
    <SafeAreaView style={s.screen}>
      <Text style={s.heading}>
        Flip Hunter
      </Text>

      {!authorized ? (
        <View style={s.form}>
          <TextInput
            style={s.input}
            placeholder="Użytkownik"
            placeholderTextColor="#888"
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
          />

          <TextInput
            style={s.input}
            placeholder="Hasło"
            placeholderTextColor="#888"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          <Pressable
            style={s.button}
            onPress={submit}
            disabled={loading}
          >
            <Text style={s.action}>
              Zaloguj
            </Text>
          </Pressable>

          <Pressable
            style={s.navButton}
            onPress={() => void diagnoseConnection()}
            disabled={checkingConnection}
          >
            <Text style={s.link}>
              Sprawdź połączenie z API
            </Text>
          </Pressable>

          {!!connectionStatus && (
            <Text style={s.muted}>
              {connectionStatus}
            </Text>
          )}
        </View>
      ) : (
        <>
          <View style={s.toolbar}>
            <Pressable
              onPress={() =>
                void loadFirst(
                  query.trim(),
                  ++version.current,
                )
              }
            >
              <Text style={s.link}>
                Odśwież radar
              </Text>
            </Pressable>

            <Pressable
              onPress={() => void logout()}
            >
              <Text style={s.link}>
                Wyloguj
              </Text>
            </Pressable>
          </View>

          <View style={s.navigation}>
            <Pressable
              style={s.navButton}
              onPress={() => {
                setSelected(null);
                setScreen('radar');
              }}
            >
              <Text style={s.link}>
                Radar
              </Text>
            </Pressable>

            <Pressable
              style={s.navButton}
              onPress={() => {
                setSelected(null);
                setScreen('calculator');
              }}
            >
              <Text style={s.link}>
                Kalkulator
              </Text>
            </Pressable>
          </View>

          {screen === 'calculator' ? (
            <FlipCalculator
              initialPurchaseMinor={
                selected?.price_minor
              }
              initialSaleMinor={
                estimatedSaleMinor
              }
              onBack={() => {
                setSelected(null);
                setScreen('radar');
              }}
            />
          ) : screen === 'details' &&
            selected ? (
            <OfferDetails
              item={selected}
              onBack={() => {
                setSelected(null);
                setScreen('radar');
              }}
              onOpen={openOriginal}
              onCalculate={() =>
                setScreen('calculator')
              }
            />
          ) : (
            <FlatList
              keyboardShouldPersistTaps="handled"
              data={visible}
              keyExtractor={
                item => String(item.snapshot_id)
              }
              ListHeaderComponent={
                <RadarPanel
                  items={items}
                  visibleCount={visible.length}
                  query={query}
                  onQuery={setQuery}
                  decision={decision}
                  onDecision={setDecision}
                  platform={platform}
                  onPlatform={setPlatform}
                  maxPrice={maxPrice}
                  onMaxPrice={setMaxPrice}
                />
              }
              refreshControl={
                <RefreshControl
                  refreshing={
                    loading && items.length > 0
                  }
                  onRefresh={() =>
                    void loadFirst(
                      query.trim(),
                      ++version.current,
                    )
                  }
                />
              }
              renderItem={({ item }) => (
                <Pressable
                  style={s.card}
                  onPress={() => {
                    setSelected(item);
                    setScreen('details');
                  }}
                >
                  <Text style={s.platform}>
                    {item.platform} · {
                      item.decision
                    }
                  </Text>

                  <Text style={s.title}>
                    {item.title ||
                      'Oferta bez tytułu'}
                  </Text>

                  <Text style={s.price}>
                    {item.price_minor === null
                      ? 'Cena nieznana'
                      : `${
                          (
                            item.price_minor / 100
                          ).toFixed(2)
                        } zł`}
                  </Text>
                </Pressable>
              )}
              ListFooterComponent={
                nextCursor !== null ? (
                  <Pressable
                    style={s.button}
                    disabled={loading}
                    onPress={() =>
                      void loadMore()
                    }
                  >
                    <Text style={s.action}>
                      Wczytaj kolejne 50 ofert
                    </Text>
                  </Pressable>
                ) : null
              }
              ListEmptyComponent={
                !loading ? (
                  <Text style={s.muted}>
                    Brak ofert dla wybranych
                    filtrów.
                  </Text>
                ) : null
              }
            />
          )}
        </>
      )}

      {loading && <ActivityIndicator />}

      {!!error && (
        <Text style={s.error}>
          {error}
        </Text>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#10141c',
    padding: 18,
  },
  heading: {
    color: '#f2f4fa',
    fontSize: 27,
    fontWeight: '700',
    marginBottom: 15,
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
    marginTop: 10,
  },
  action: {
    color: 'white',
    textAlign: 'center',
    fontWeight: '700',
  },
  toolbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  link: {
    color: '#99b6ff',
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
  muted: {
    color: '#a5acb8',
  },
  error: {
    color: '#ff8585',
    marginTop: 12,
  },
});
