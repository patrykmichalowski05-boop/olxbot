import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type Href, usePathname, useRouter } from 'expo-router';

import { useAuth } from '@/features/auth/AuthContext';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { useTheme } from '@/theme/ThemeProvider';

const destinations: { href: Href; prefix: string; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { href: '/dashboard', prefix: '/dashboard', label: 'Dashboard', icon: 'grid-outline' },
  { href: '/radar', prefix: '/radar', label: 'Radar', icon: 'radio-outline' },
  { href: '/watched', prefix: '/watched', label: 'Obserwowane', icon: 'bookmark-outline' },
  { href: '/analyze', prefix: '/analyze', label: 'Analiza AI', icon: 'scan-outline' },
  { href: '/flips', prefix: '/flips', label: 'Moje flipy', icon: 'briefcase-outline' },
  { href: '/analytics', prefix: '/analytics', label: 'Analityka', icon: 'bar-chart-outline' },
  { href: '/notifications', prefix: '/notifications', label: 'Powiadomienia', icon: 'notifications-outline' },
  { href: '/settings', prefix: '/settings', label: 'Ustawienia', icon: 'settings-outline' },
];

/** One shell around the root stack keeps the sidebar on detail routes as well. */
export function DesktopLayout({ children }: { children: React.ReactNode }) {
  const { colors, typography } = useTheme();
  const { isMobile, isDesktop, sidebarWidth, pagePadding } = useResponsiveLayout();
  const { signedIn, mode, userId } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [search, setSearch] = useState('');
  const visible = !isMobile && signedIn && pathname !== '/login';
  const active = destinations.find((item) => pathname.startsWith(item.prefix));
  const title = active?.label ?? (pathname.startsWith('/offer') ? 'Szczegóły oferty' : 'Zapis zakupu');

  const submitSearch = () => {
    router.push({ pathname: '/radar', params: { search: search.trim() } });
  };

  return (
    <View style={[styles.root, { backgroundColor: colors.background, flexDirection: visible ? 'row' : 'column' }]}>
      {visible ? (
        <View style={[styles.sidebar, { width: sidebarWidth, backgroundColor: colors.sidebar, borderColor: colors.border }]}>
          <Pressable accessibilityRole="button" accessibilityLabel="FlipRadar — dashboard" onPress={() => router.push('/dashboard')} style={styles.brand}>
            <View style={[styles.brandIcon, { backgroundColor: colors.accentMuted }]}>
              <Ionicons name="radio" size={25} color={colors.accent} />
            </View>
            {isDesktop ? <View style={{ gap: 2 }}>
              <Text style={[typography.headline, { color: colors.text }]}>FlipRadar</Text>
              <Text style={[typography.caption, { color: colors.textMuted }]}>Twoje centrum okazji</Text>
            </View> : null}
          </Pressable>
          <ScrollView contentContainerStyle={styles.nav}>
            {isDesktop ? <Text style={[styles.navLabel, { color: colors.textMuted }]}>PRZESTRZEŃ ROBOCZA</Text> : null}
            {destinations.map((item) => {
              const selected = active?.prefix === item.prefix;
              return (
                <Pressable key={item.prefix} accessibilityRole="button" accessibilityLabel={item.label} accessibilityState={{ selected }}
                  onPress={() => router.push(item.href)}
                  style={({ pressed }) => [styles.navItem, {
                    backgroundColor: selected ? colors.accentMuted : pressed ? colors.surface : 'transparent',
                    borderLeftColor: selected ? colors.accent : 'transparent',
                    justifyContent: isDesktop ? 'flex-start' : 'center',
                  }]}>
                  <Ionicons name={item.icon} size={21} color={selected ? colors.accent : colors.textMuted} />
                  {isDesktop ? <Text style={[typography.bodyStrong, { color: selected ? colors.accent : colors.textMuted }]}>{item.label}</Text> : null}
                </Pressable>
              );
            })}
          </ScrollView>
          <View style={[styles.account, { borderColor: colors.border }]}>
            <View style={[styles.avatar, { backgroundColor: colors.surface }]}><Ionicons name="person-outline" size={20} color={colors.textMuted} /></View>
            {isDesktop ? <View style={{ flex: 1, gap: 3 }}>
              <Text style={[typography.bodyStrong, { color: colors.text }]} numberOfLines={1}>{mode === 'demo' ? 'Konto demonstracyjne' : userId ?? 'Twoje konto'}</Text>
              <Text style={[typography.caption, { color: colors.textMuted }]}>FlipRadar · {mode.toUpperCase()}</Text>
            </View> : null}
          </View>
        </View>
      ) : null}
      <View style={styles.main}>
        {visible ? (
          <View style={[styles.topbar, { backgroundColor: colors.sidebar, borderColor: colors.border, paddingHorizontal: pagePadding }]}>
            <View style={styles.breadcrumb}>
              {isDesktop ? <Text style={[typography.caption, { color: colors.textMuted }]}>Przestrzeń robocza</Text> : null}
              <Text style={[typography.bodyStrong, { color: colors.text }]} numberOfLines={1}>{title}</Text>
            </View>
            <View style={[styles.search, { borderColor: colors.border, backgroundColor: colors.background }]}>
              <Ionicons name="search-outline" size={18} color={colors.textMuted} />
              <TextInput accessibilityLabel="Szukaj ofert w radarze" placeholder="Szukaj marki, modelu, okazji…" placeholderTextColor={colors.textMuted}
                value={search} onChangeText={setSearch} onSubmitEditing={submitSearch} returnKeyType="search"
                style={[styles.searchInput, { color: colors.text }]} />
              <Pressable accessibilityRole="button" accessibilityLabel="Wyszukaj" onPress={submitSearch} style={styles.searchAction}>
                <Ionicons name="arrow-forward-outline" size={18} color={colors.accent} />
              </Pressable>
            </View>
            <View style={[styles.mode, { borderColor: colors.border }]}><View style={[styles.dot, { backgroundColor: mode === 'demo' ? colors.risk : colors.accent }]} /><Text style={[typography.caption, { color: colors.textMuted }]}>{mode.toUpperCase()}</Text></View>
            <Pressable accessibilityRole="button" accessibilityLabel="Otwórz powiadomienia" onPress={() => router.push('/notifications')}
              style={[styles.bell, { borderColor: colors.border }]}>
              <Ionicons name="notifications-outline" size={21} color={colors.text} />
            </Pressable>
          </View>
        ) : null}
        <View style={styles.content}>{children}</View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, minWidth: 0, minHeight: 0 },
  sidebar: { borderRightWidth: 1, paddingTop: 24, paddingBottom: 20 },
  brand: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 20, marginBottom: 32, minHeight: 48 },
  brandIcon: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  nav: { paddingHorizontal: 12, gap: 6 },
  navLabel: { fontSize: 10, fontWeight: '600', letterSpacing: 1.2, marginBottom: 10, marginLeft: 14 },
  navItem: { minHeight: 48, borderRadius: 12, borderLeftWidth: 3, flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 12 },
  account: { marginTop: 24, paddingTop: 20, marginHorizontal: 20, borderTopWidth: 1, flexDirection: 'row', gap: 10, alignItems: 'center' },
  avatar: { width: 38, height: 38, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  main: { flex: 1, minWidth: 0, minHeight: 0 },
  content: { flex: 1, minHeight: 0 },
  topbar: { minHeight: 80, paddingVertical: 14, borderBottomWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 16 },
  breadcrumb: { flex: 1, minWidth: 0, gap: 4 },
  search: { flex: 1, maxWidth: 440, minWidth: 180, flexDirection: 'row', alignItems: 'center', gap: 10, paddingLeft: 12, borderWidth: 1, borderRadius: 12 },
  searchInput: { flex: 1, minWidth: 0, fontSize: 13, height: 44 },
  searchAction: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  mode: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 10, height: 32, flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 6, height: 6, borderRadius: 3 },
  bell: { width: 44, height: 44, borderWidth: 1, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
});
