import React, { useState } from "react";
import {
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { usePathname, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { getAccount } from "@/api/endpoints/portal";
import { apiErrorMessage } from "@/api/errors";
import { useAuth } from "@/features/auth/AuthContext";
import { useTheme } from "@/theme/ThemeProvider";
import { layout } from "@/theme/tokens";
import { portalEnabled } from "@/utils/config";
import { IconButton, type IconName } from "@/components/IconButton";
import { useRuntimeCapabilities } from "@/features/runtime/useRuntimeCapabilities";
import { WorkspaceNotice } from "./WorkspaceNotice";
import { WorkspaceContext, useWorkspaceLayout } from "./layout";

const navigation: {
  title: string;
  items: { label: string; href: string; icon: IconName }[];
}[] = [
  {
    title: "CENTRUM",
    items: [
      { label: "Flip Radar", href: "/radar", icon: "radio-outline" },
      { label: "Moje wyszukiwania", href: "/searches", icon: "list-outline" },
    ],
  },
  {
    title: "NARZĘDZIA",
    items: [
      { label: "Dane rynku", href: "/market", icon: "stats-chart-outline" },
      { label: "Analiza oferty", href: "/analyze", icon: "scan-outline" },
      { label: "Zapisane", href: "/watched", icon: "bookmark-outline" },
    ],
  },
  {
    title: "TWOJE FLIPY",
    items: [
      { label: "Moje flipy", href: "/flips", icon: "briefcase-outline" },
      {
        label: "Powiadomienia",
        href: "/notifications",
        icon: "notifications-outline",
      },
      { label: "Ustawienia", href: "/settings", icon: "settings-outline" },
    ],
  },
];

export function BotShell({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const runtime = useRuntimeCapabilities();
  const router = useRouter();
  const pathname = usePathname();
  const { colors, typography, radii } = useTheme();
  const insets = useSafeAreaInsets();
  const { inside, desktop, contentWidth } = useWorkspaceLayout();
  const [open, setOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);
  const account = useQuery({
    queryKey: ["portal-account", auth.userId],
    queryFn: ({ signal }) => getAccount(signal),
    enabled:
      auth.ready && auth.signedIn && auth.mode === "live" && portalEnabled(),
    staleTime: 15000,
    refetchInterval: 60000,
  });

  if (inside || !auth.ready || !auth.signedIn) return <>{children}</>;

  const demo = auth.mode === "demo";
  const plan = account.data?.plan;
  const access = account.data?.access;
  const limit = access?.limit ?? (demo ? 3 : null);
  const used = access?.used ?? 0;
  const username =
    account.data?.username ?? (demo ? "Konto demo" : "Twoje konto");
  const quota =
    limit === null ? "Dostęp bez limitu" : `${used}/${limit} wyszukiwań`;
  const quotaReady = Boolean(account.data) || demo;
  const go = (href: string) => {
    setOpen(false);
    router.navigate(href as never);
  };
  const logout = async () => {
    setLoggingOut(true);
    setLogoutError("");
    try {
      await auth.logout();
    } catch (error) {
      setLogoutError(apiErrorMessage(error));
    } finally {
      setLoggingOut(false);
    }
  };
  const logo = (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel="FlipRadar — radar okazji"
      onPress={() => go("/radar")}
    >
      <Text
        style={{
          fontSize: 20,
          fontWeight: "800",
          letterSpacing: -0.6,
          color: colors.text,
        }}
      >
        Flip<Text style={{ color: colors.accent }}>Radar</Text>
      </Text>
    </Pressable>
  );
  const menu = (drawer = false) => (
    <View
      style={[
        styles.menu,
        {
          backgroundColor: colors.navigation,
          paddingTop: drawer ? insets.top + 20 : Math.max(insets.top, 24),
        },
      ]}
    >
      <View style={styles.brand}>
        {logo}
        {drawer ? (
          <IconButton
            label="Zamknij menu"
            icon="close-outline"
            onPress={() => setOpen(false)}
          />
        ) : null}
      </View>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.menuScroll}
      >
        {navigation.map((group) => (
          <View key={group.title} style={{ marginBottom: 16 }}>
            <Text
              style={[
                typography.caption,
                {
                  color: colors.textMuted,
                  fontWeight: "700",
                  letterSpacing: 0.8,
                  marginHorizontal: 10,
                  marginBottom: 6,
                },
              ]}
            >
              {group.title}
            </Text>
            {group.items.map((item) => {
              const active =
                pathname === item.href ||
                (item.href === "/searches" &&
                  pathname.startsWith("/searches/"));
              return (
                <Pressable
                  key={item.href}
                  accessibilityRole="link"
                  accessibilityState={{ selected: active }}
                  onPress={() => go(item.href)}
                  style={({ pressed }) => [
                    styles.navItem,
                    {
                      backgroundColor: active
                        ? colors.accentBg
                        : pressed
                          ? colors.surfaceElevated
                          : "transparent",
                      borderRadius: radii.md,
                    },
                  ]}
                >
                  <Ionicons
                    name={item.icon}
                    size={17}
                    color={active ? colors.accent : colors.textMuted}
                  />
                  <Text
                    style={[
                      typography.body,
                      {
                        color: active ? colors.accent : colors.text,
                        fontWeight: active ? "700" : "500",
                      },
                    ]}
                  >
                    {item.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        ))}
        <View style={{ flex: 1, minHeight: 20 }} />
        <Pressable
          accessibilityRole="link"
          accessibilityLabel="Sprawdź swój pakiet i wykorzystane wyszukiwania"
          onPress={() => go("/account")}
          style={{
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: radii.lg,
            backgroundColor: colors.surface,
            padding: 12,
            gap: 8,
          }}
        >
          <View style={styles.row}>
            <Text
              style={[
                typography.caption,
                { color: colors.text, fontWeight: "700", flex: 1 },
              ]}
            >
              Wyszukiwania
            </Text>
            {demo ? (
              <Text
                style={[
                  typography.caption,
                  {
                    color: colors.accent,
                    backgroundColor: colors.accentBg,
                    borderRadius: 20,
                    paddingHorizontal: 8,
                    paddingVertical: 3,
                  },
                ]}
              >
                Demo
              </Text>
            ) : null}
          </View>
          {quotaReady ? (
            <>
              <View
                accessibilityRole="progressbar"
                accessibilityLabel="Wykorzystane wyszukiwania"
                accessibilityValue={
                  limit === null
                    ? { text: "Bez limitu" }
                    : { min: 0, max: limit, now: Math.min(used, limit) }
                }
                style={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: colors.surfaceElevated,
                  overflow: "hidden",
                }}
              >
                <View
                  style={{
                    height: 8,
                    width:
                      limit === null
                        ? "100%"
                        : `${Math.min(100, Math.max(0, (used / Math.max(1, limit)) * 100))}%`,
                    backgroundColor: colors.primary,
                  }}
                />
              </View>
              <Text style={[typography.caption, { color: colors.textMuted }]}>
                {limit === null
                  ? quota
                  : `Wykorzystano ${used} z ${limit} wyszukiwań`}
              </Text>
            </>
          ) : (
            <Text style={[typography.caption, { color: colors.textMuted }]}>
              {account.isError
                ? "Sprawdź dostęp na koncie"
                : portalEnabled()
                  ? "Sprawdzamy Twój pakiet…"
                  : "Przejdź do swojego konta"}
            </Text>
          )}
        </Pressable>
        <Pressable
          accessibilityRole="link"
          onPress={() => go("/account")}
          style={[styles.row, { gap: 10, padding: 10, marginTop: 12 }]}
        >
          <View
            style={{
              width: 36,
              height: 36,
              borderRadius: 18,
              backgroundColor: "#FFC067",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Text style={{ color: "#172D40", fontSize: 15, fontWeight: "700" }}>
              {username[0]?.toUpperCase()}
            </Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text
              numberOfLines={1}
              style={[typography.bodyStrong, { color: colors.text }]}
            >
              {username}
            </Text>
            <Text style={[typography.caption, { color: colors.textMuted }]}>
              {plan?.name ?? (demo ? "Start · przykład" : "Moje konto")}
            </Text>
            <Text
              style={[
                typography.caption,
                { color: colors.accent, textDecorationLine: "underline" },
              ]}
            >
              Moje konto
            </Text>
          </View>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          disabled={loggingOut}
          onPress={() => {
            void logout();
          }}
          style={[styles.navItem, { marginTop: 6 }]}
        >
          <Ionicons name="log-out-outline" size={17} color={colors.textMuted} />
          <Text style={[typography.body, { color: colors.textMuted }]}>
            {loggingOut ? "Wylogowujemy…" : "Wyloguj"}
          </Text>
        </Pressable>
        {logoutError ? (
          <Text
            accessibilityLiveRegion="polite"
            style={[typography.caption, { color: colors.loss, margin: 10 }]}
          >
            {logoutError}
          </Text>
        ) : null}
      </ScrollView>
    </View>
  );
  return (
    <WorkspaceContext.Provider value>
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        {desktop ? (
          <View
            style={{
              width: layout.sidebarWidth,
              borderRightWidth: 1,
              borderColor: colors.border,
            }}
          >
            {menu()}
          </View>
        ) : null}
        <View style={{ flex: 1, minWidth: 0 }}>
          {!desktop ? (
            <View
              style={[
                styles.mobileHeader,
                {
                  borderColor: colors.border,
                  backgroundColor: colors.navigation,
                  paddingTop: insets.top + 16,
                  paddingBottom: 16,
                  paddingLeft: insets.left + 20,
                  paddingRight: insets.right + 20,
                },
              ]}
            >
              {logo}
              <View
                style={{ flexDirection: "row", alignItems: "center", gap: 10 }}
              >
                <Pressable
                  accessibilityRole="link"
                  onPress={() => go("/account")}
                  style={{
                    borderRadius: 20,
                    backgroundColor: colors.accentBg,
                    paddingVertical: 7,
                    paddingHorizontal: 10,
                  }}
                >
                  <Text
                    style={[
                      typography.caption,
                      { color: colors.accent, fontWeight: "700" },
                    ]}
                  >
                    {quotaReady
                      ? `${contentWidth < 410 && limit !== null ? `${used}/${limit}` : quota}${demo ? " · demo" : ""}`
                      : "Moje konto"}
                  </Text>
                </Pressable>
                <IconButton
                  label="Otwórz menu"
                  icon="menu-outline"
                  onPress={() => setOpen(true)}
                  active={open}
                />
              </View>
            </View>
          ) : null}
          {runtime.capabilities.read_only ? (
            <View style={{ padding: 12 }}>
              <WorkspaceNotice text="Oglądasz podgląd. Zmiany danych są wyłączone." />
            </View>
          ) : null}
          {children}
        </View>
      </View>
      <Modal
        visible={open && !desktop}
        transparent
        animationType="fade"
        onRequestClose={() => setOpen(false)}
        statusBarTranslucent
      >
        <View style={{ flex: 1, backgroundColor: colors.overlay }}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Zamknij menu"
            onPress={() => setOpen(false)}
            style={StyleSheet.absoluteFill}
          />
          <View
            accessibilityViewIsModal
            style={{
              width: "88%",
              maxWidth: 320,
              height: "100%",
              paddingBottom: insets.bottom,
              backgroundColor: colors.navigation,
            }}
          >
            {menu(true)}
          </View>
        </View>
      </Modal>
    </WorkspaceContext.Provider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, flexDirection: "row", minHeight: 0 },
  menu: { flex: 1 },
  brand: {
    paddingHorizontal: 24,
    marginBottom: 32,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  menuScroll: {
    flexGrow: 1,
    paddingHorizontal: 14,
    paddingBottom: Platform.OS === "web" ? 24 : 16,
  },
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  navItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    minHeight: 40,
    paddingHorizontal: 10,
    paddingVertical: 10,
  },
  mobileHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    gap: 8,
  },
});
