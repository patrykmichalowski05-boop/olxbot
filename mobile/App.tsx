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
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');

    try {
      setItems(await getRadar());
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

  async function logout() {
    await clearSession();
    setAuthorized(false);
    setItems([]);
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

          <FlatList
            data={items}
            keyExtractor={(item) => String(item.snapshot_id)}
            renderItem={({ item }) => (
              <Pressable
                style={styles.card}
                onPress={() => openOriginal(item.url)}
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
            ListEmptyComponent={
              !loading
                ? <Text style={styles.muted}>Brak ofert</Text>
                : null
            }
          />
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
  muted: {
    color: '#a5acb8',
  },
  error: {
    color: '#ff8585',
    marginTop: 12,
  },
});
