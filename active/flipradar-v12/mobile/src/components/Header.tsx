import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useTheme } from "@/theme/ThemeProvider";
import { IconButton } from "./IconButton";
import { useWorkspaceLayout } from "@/features/workspace/layout";

type Props = {
  title: string;
  subtitle?: string;
  showBack?: boolean;
  onBack?: () => void;
  rightSlot?: React.ReactNode;
  showNotifications?: boolean;
  backLabel?: string;
};
export function Header({
  title,
  subtitle,
  showBack,
  onBack,
  rightSlot,
  showNotifications = false,
  backLabel = "Wróć",
}: Props) {
  const { colors, spacing, typography } = useTheme();
  const router = useRouter();
  const { inside, pagePadding, narrow } = useWorkspaceLayout();
  if (inside)
    return (
      <View
        style={{
          marginHorizontal: -pagePadding,
          paddingHorizontal: pagePadding,
          paddingVertical: showBack ? (narrow ? 24 : 18) : 22,
          minHeight: 90,
          gap: 4,
          borderBottomWidth: 1,
          borderColor: colors.border,
          backgroundColor: colors.surface,
          marginBottom: 28,
        }}
      >
        {showBack ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={backLabel}
            hitSlop={12}
            onPress={
              onBack ??
              (() =>
                router.canGoBack() ? router.back() : router.replace("/radar"))
            }
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 4,
              alignSelf: "flex-start",
              minHeight: 21,
            }}
          >
            <Ionicons name="arrow-back" size={14} color={colors.accent} />
            <Text
              style={[
                typography.body,
                { color: colors.accent, fontWeight: "600" },
              ]}
            >
              {backLabel}
            </Text>
          </Pressable>
        ) : null}
        <View style={styles.row}>
          <View style={styles.titleWrap}>
            <Text
              accessibilityRole="header"
              style={[typography.title, { color: colors.text }]}
            >
              {title}
            </Text>
            {subtitle ? (
              <Text
                style={[
                  typography.caption,
                  { color: colors.textMuted, marginTop: 2 },
                ]}
              >
                {subtitle}
              </Text>
            ) : null}
          </View>
          <View style={styles.actions}>
            {rightSlot}
            {showNotifications ? (
              <IconButton
                icon="notifications-outline"
                label="Powiadomienia"
                onPress={() => router.push("/notifications")}
              />
            ) : null}
          </View>
        </View>
      </View>
    );
  return (
    <View style={[styles.row, { marginBottom: spacing.lg, gap: spacing.md }]}>
      {showBack ? (
        <IconButton
          icon="chevron-back"
          label="Wróć"
          onPress={onBack ?? (() => router.back())}
        />
      ) : null}
      <View style={styles.titleWrap}>
        {!showBack ? (
          <Text
            style={[
              typography.label,
              { color: colors.accent, marginBottom: 4 },
            ]}
          >
            FLIPRADAR
          </Text>
        ) : null}
        <Text
          style={[typography.title, { color: colors.text }]}
          numberOfLines={1}
          adjustsFontSizeToFit
          minimumFontScale={0.8}
        >
          {title}
        </Text>
        {subtitle ? (
          <Text
            style={[
              typography.caption,
              { color: colors.textMuted, marginTop: 4 },
            ]}
          >
            {subtitle}
          </Text>
        ) : null}
      </View>
      <View style={styles.actions}>
        {rightSlot}
        {showNotifications ? (
          <IconButton
            icon="notifications-outline"
            label="Powiadomienia"
            onPress={() => router.push("/notifications")}
          />
        ) : null}
      </View>
    </View>
  );
}
const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center" },
  titleWrap: { flex: 1, minWidth: 0 },
  actions: { flexDirection: "row", alignItems: "center", gap: 8 },
});
